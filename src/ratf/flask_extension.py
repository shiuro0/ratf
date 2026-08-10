from __future__ import annotations

from functools import wraps
from typing import Any, Callable, Mapping

from flask import Blueprint, Flask, current_app, g, jsonify, make_response, request

from .auth import extract_bearer_token
from .config import Settings
from .context import extract_context
from .core.config import CoreConfig
from .core.engine import RATFEngine
from .core.models import EvaluationRequest, EvaluationResult
from .core.profile import PolicyProfile
from .identity import LocalRegistryIdentityProvider
from .logging_utils import AuditLogger
from .storage import Storage, create_storage


class RATF:
    """Flask extension that adapts HTTP requests to the R-ATF core."""

    def __init__(
        self,
        app: Flask | None = None,
        *,
        settings: Settings | None = None,
        storage: Storage | None = None,
        identity_provider=None,
        step_up_handler=None,
        audit_logger: AuditLogger | None = None,
    ):
        self.settings = settings
        self.storage = storage
        self.identity_provider = identity_provider
        self.step_up_handler = step_up_handler
        self.audit_logger = audit_logger
        self.engine: RATFEngine | None = None
        self.policies: dict[str, PolicyProfile] = {}
        if app is not None:
            self.init_app(app)

    def init_app(self, app: Flask) -> None:
        app.config.setdefault("RATF_SHADOW_MODE", False)
        app.config.setdefault("RATF_DASHBOARD_ENABLED", False)
        app.config.setdefault("RATF_DASHBOARD_UNSAFE_LOCAL", False)
        app.config.setdefault("RATF_DASHBOARD_KEY", "")
        app.config.setdefault("RATF_DASHBOARD_DEFAULT_POLICY", "")
        app.config.setdefault("RATF_DASHBOARD_DEMO_CONTEXT", None)
        app.config.setdefault("RATF_RESEARCH_RESULTS_DIR", "")
        app.config.setdefault("RATF_AUTHZEN_ENABLED", False)
        app.config.setdefault("RATF_AUTHZEN_API_KEY", "")
        app.config.setdefault("RATF_POLICIES", {})

        settings = self.settings or app.config.get("RATF_SETTINGS") or Settings()
        storage = self.storage or app.config.get("RATF_STORAGE") or create_storage(settings)
        audit_logger = self.audit_logger or app.config.get("RATF_AUDIT_LOGGER")
        if audit_logger is None:
            audit_logger = AuditLogger(settings.log_path, settings.audit_log_secret)
        identity_provider = self.identity_provider or app.config.get("RATF_IDENTITY_PROVIDER")
        if identity_provider is None:
            identity_provider = LocalRegistryIdentityProvider(settings, storage)
        step_up_handler = self.step_up_handler or app.config.get("RATF_STEP_UP_HANDLER")

        core_config = app.config.get("RATF_CORE_CONFIG") or CoreConfig.from_settings(
            settings,
            shadow_mode=bool(app.config["RATF_SHADOW_MODE"]),
        )
        self.settings = settings
        self.storage = storage
        self.identity_provider = identity_provider
        self.step_up_handler = step_up_handler
        self.audit_logger = audit_logger
        self.engine = RATFEngine(
            core_config,
            storage,
            identity_provider=identity_provider,
            step_up_handler=step_up_handler,
            event_handler=audit_logger.write,
        )
        app.extensions["ratf"] = self

        configured_policies = app.config.get("RATF_POLICIES") or {}
        if not isinstance(configured_policies, Mapping):
            raise TypeError("RATF_POLICIES harus berupa mapping nama ke konfigurasi policy")
        for name, values in configured_policies.items():
            if isinstance(values, PolicyProfile):
                profile = values
            elif isinstance(values, Mapping):
                profile = self._make_policy(str(name), **dict(values))
            else:
                raise TypeError(f"Konfigurasi policy {name!r} harus berupa mapping")
            self.policies[profile.name] = profile
        for profile in self.policies.values():
            profile.resolve(self.engine.config)

        if app.config["RATF_AUTHZEN_ENABLED"]:
            from .authzen import create_authzen_blueprint

            app.register_blueprint(
                create_authzen_blueprint(
                    self.engine,
                    str(app.config["RATF_AUTHZEN_API_KEY"]),
                    policy_resolver=self.resolve_policy,
                )
            )
        if app.config["RATF_DASHBOARD_ENABLED"]:
            from .dashboard import create_dashboard_blueprint

            app.register_blueprint(create_dashboard_blueprint())

    def protect(
        self,
        required_scope: str | None = None,
        *,
        transactional: bool = False,
        policy: PolicyProfile | str | None = None,
    ) -> Callable:
        def decorator(view_func: Callable) -> Callable:
            @wraps(view_func)
            def wrapper(*args, **kwargs):
                extension: RATF = current_app.extensions["ratf"]
                result = extension._evaluate_http_request(
                    required_scope=required_scope,
                    transactional=transactional,
                    policy=policy,
                )
                if result.allowed:
                    return extension._decorate(make_response(view_func(*args, **kwargs)), result)
                return extension._rejection(result)

            return wrapper

        return decorator

    def protect_blueprint(
        self,
        blueprint: Blueprint,
        *,
        required_scope: str | None = None,
        transactional: bool = False,
        policy: PolicyProfile | str | None = None,
        include_options: bool = False,
    ) -> Blueprint:
        """Apply one R-ATF policy to every route in a Flask Blueprint.

        Register this hook before ``app.register_blueprint`` and do not combine
        it with ``@ratf.protect`` on the same route.
        """

        @blueprint.before_request
        def ratf_blueprint_before_request():
            if request.method == "OPTIONS" and not include_options:
                return None
            extension: RATF = current_app.extensions["ratf"]
            result = extension._evaluate_http_request(
                required_scope=required_scope,
                transactional=transactional,
                policy=policy,
            )
            return None if result.allowed else extension._rejection(result)

        @blueprint.after_request
        def ratf_blueprint_after_request(response):
            result = getattr(g, "ratf", None)
            if result is None:
                return response
            return current_app.extensions["ratf"]._decorate(make_response(response), result)

        return blueprint

    def _evaluate_http_request(
        self,
        *,
        required_scope: str | None,
        transactional: bool,
        policy: PolicyProfile | str | None,
    ) -> EvaluationResult:
        assert self.engine is not None and self.settings is not None
        context = extract_context(request, self.settings)
        token = extract_bearer_token(request.headers.get("Authorization"))
        result = self.engine.evaluate_token(
            token,
            EvaluationRequest(
                context=context,
                required_scope=required_scope,
                transactional=transactional,
                policy=self.resolve_policy(policy),
            ),
        )
        g.ratf = result
        return result

    def policy(
        self,
        name: str,
        *,
        weights: Mapping[str, float] | None = None,
        thresholds: Mapping[str, float] | None = None,
        verify_threshold: float | None = None,
        allow_threshold: float | None = None,
        shadow_mode: bool | None = None,
        burst_soft_limit: int | None = None,
        burst_hard_limit: int | None = None,
        hard_burst_block: bool | None = None,
    ) -> PolicyProfile:
        """Create and register a reusable named policy profile."""

        if name in self.policies:
            raise ValueError(f"Policy {name!r} sudah terdaftar")
        profile = self._make_policy(
            name,
            weights=weights,
            thresholds=thresholds,
            verify_threshold=verify_threshold,
            allow_threshold=allow_threshold,
            shadow_mode=shadow_mode,
            burst_soft_limit=burst_soft_limit,
            burst_hard_limit=burst_hard_limit,
            hard_burst_block=hard_burst_block,
        )
        if self.engine is not None:
            profile.resolve(self.engine.config)
        self.policies[profile.name] = profile
        return profile

    def debug_snapshot(self, family_id: str | None = None, *, limit: int = 20) -> dict[str, Any]:
        """Return safe runtime information for application-owned debugging.

        Raw access tokens, request signatures, and Redis credentials are never
        included. Applications must protect any HTTP endpoint that exposes this
        information and should disable it outside development environments.
        """

        if self.engine is None or self.storage is None:
            raise RuntimeError("RATF belum diinisialisasi pada aplikasi")

        snapshot: dict[str, Any] = {
            "storage_backend": self.storage.backend_name,
            "recent_events": self.engine.recent_events(limit),
        }
        if family_id is not None:
            key = str(family_id).strip()
            if not key:
                raise ValueError("family_id tidak boleh kosong")
            snapshot.update(
                {
                    "family_id": key,
                    "context_profile": self.storage.get_json(f"family_context:{key}") or {},
                    "context_history": self.storage.get_json(f"family_history:{key}") or {},
                }
            )
        return snapshot

    @staticmethod
    def _make_policy(
        name: str,
        *,
        weights: Mapping[str, float] | None = None,
        thresholds: Mapping[str, float] | None = None,
        verify_threshold: float | None = None,
        allow_threshold: float | None = None,
        shadow_mode: bool | None = None,
        burst_soft_limit: int | None = None,
        burst_hard_limit: int | None = None,
        hard_burst_block: bool | None = None,
    ) -> PolicyProfile:
        threshold_values = dict(thresholds or {})
        unknown = set(threshold_values) - {"verify", "allow"}
        if unknown:
            raise ValueError(f"Nama threshold tidak dikenal: {', '.join(sorted(unknown))}")
        if verify_threshold is not None and "verify" in threshold_values:
            raise ValueError("Gunakan salah satu: thresholds['verify'] atau verify_threshold")
        if allow_threshold is not None and "allow" in threshold_values:
            raise ValueError("Gunakan salah satu: thresholds['allow'] atau allow_threshold")
        return PolicyProfile(
            name=name,
            weights=dict(weights or {}),
            verify_threshold=verify_threshold
            if verify_threshold is not None
            else threshold_values.get("verify"),
            allow_threshold=allow_threshold
            if allow_threshold is not None
            else threshold_values.get("allow"),
            shadow_mode=shadow_mode,
            burst_soft_limit=burst_soft_limit,
            burst_hard_limit=burst_hard_limit,
            hard_burst_block=hard_burst_block,
        )

    def resolve_policy(self, policy: PolicyProfile | str | None) -> PolicyProfile | None:
        if policy is None:
            return None
        if isinstance(policy, PolicyProfile):
            return policy
        try:
            return self.policies[str(policy)]
        except KeyError as exc:
            raise ValueError(f"Policy {policy!r} belum terdaftar") from exc

    def policy_config(self, name: str) -> dict[str, Any]:
        if not self.engine:
            raise RuntimeError("RATF.init_app() belum dipanggil")
        profile = self.resolve_policy(name)
        assert profile is not None
        return profile.to_dict(self.engine.config)

    def update_policy(self, **values: Any) -> dict[str, Any]:
        if not self.engine:
            raise RuntimeError("RATF.init_app() belum dipanggil")
        self.engine.config.update_policy(**values)
        return self.engine.config.to_dict()

    def update_policy_profile(self, name: str, **values: Any) -> dict[str, Any]:
        """Update a named policy without editing the protected endpoint.

        Dashboard integrations can use this method during development. The
        decorator should refer to the policy by name so each request resolves
        the latest profile.
        """

        if not self.engine:
            raise RuntimeError("RATF.init_app() belum dipanggil")
        current = self.resolve_policy(name)
        if current is None:
            raise ValueError(f"Policy {name!r} belum terdaftar")

        updated = PolicyProfile(
            name=current.name,
            weights=dict(values.get("weights", current.weights)),
            verify_threshold=values.get(
                "verify_threshold", current.verify_threshold
            ),
            allow_threshold=values.get("allow_threshold", current.allow_threshold),
            shadow_mode=values.get("shadow_mode", current.shadow_mode),
            burst_soft_limit=values.get(
                "burst_soft_limit", current.burst_soft_limit
            ),
            burst_hard_limit=values.get(
                "burst_hard_limit", current.burst_hard_limit
            ),
            hard_burst_block=values.get(
                "hard_burst_block", current.hard_burst_block
            ),
        )
        updated.resolve(self.engine.config)
        self.policies[current.name] = updated
        return updated.to_dict(self.engine.config)

    @staticmethod
    def _decorate(response, result: EvaluationResult):
        response.headers["X-RATF-Decision"] = result.decision
        response.headers["X-RATF-Effective-Decision"] = result.effective_decision
        response.headers["X-RATF-Reason"] = result.reason_code
        response.headers["X-RATF-Shadow-Mode"] = str(result.shadow_mode).lower()
        response.headers["X-RATF-Policy"] = result.policy_name
        if result.trust_score is not None:
            response.headers["X-RATF-Score"] = str(result.trust_score)
        return response

    def _rejection(self, result: EvaluationResult):
        body: dict[str, Any] = {
            "status": "verification_required" if result.decision == "verify" else "rejected",
            **result.to_dict(),
        }
        response = jsonify(body)
        response.status_code = result.http_status
        response.headers["Cache-Control"] = "no-store"
        if result.decision == "verify":
            response.headers["WWW-Authenticate"] = (
                'Bearer error="insufficient_user_authentication"'
            )
        return self._decorate(response, result)
