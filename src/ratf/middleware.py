"""Compatibility adapter for reproducing the original v6 experiments.

New applications should use :class:`ratf.flask_extension.RATF`. This module is
kept behaviorally stable so earlier Standard API/R-ATF evidence can still be
reproduced; both paths import the same trust-score and policy functions.
"""

from __future__ import annotations

import hashlib
import hmac
import time
from functools import wraps
from typing import Callable

from flask import jsonify, make_response, request

from .auth import extract_bearer_token, record_token_use, validate_access_token
from .config import Settings
from .context import extract_context
from .device_proof import verify_device_proof
from .logging_utils import AuditLogger
from .policy import PolicyDecision, decide
from .replay import check_replay
from .storage import Storage
from .trust_score import compute_trust_score, record_context_history


def _ttl(meta: dict) -> int:
    return max(int(meta.get("exp", 0)) - int(time.time()), 1)


def _has_scope(meta: dict, required: str | None) -> bool:
    if not required:
        return True
    return required in set(meta.get("scopes") or str(meta.get("scope", "")).split())


class SecurityMiddleware:
    def __init__(self, settings: Settings, storage: Storage, audit_logger: AuditLogger, mode: str):
        self.settings = settings
        self.storage = storage
        self.audit_logger = audit_logger
        self.mode = mode

    def protect(self, required_scope: str | None = None, transactional: bool = False) -> Callable:
        def decorator(view_func: Callable) -> Callable:
            @wraps(view_func)
            def wrapper(*args, **kwargs):
                started = time.perf_counter()
                context = extract_context(request, self.settings)
                token = extract_bearer_token(request.headers.get("Authorization"))
                token_hash, meta = "missing", {}
                score, components, count = None, {}, None
                reasons: list[str] = []

                if not token:
                    return self._reject(
                        context,
                        token_hash,
                        meta,
                        score,
                        components,
                        PolicyDecision("block", 401, "missing_bearer_token"),
                        reasons,
                        started,
                    )

                validation = validate_access_token(token, self.settings, self.storage)
                token_hash, meta = validation.token_id_hash, validation.metadata or {}
                if not validation.valid:
                    return self._reject(
                        context,
                        token_hash,
                        meta,
                        score,
                        components,
                        PolicyDecision("block", 401, validation.error or "invalid_token"),
                        reasons,
                        started,
                    )
                if context.client_id != meta.get("client_id"):
                    return self._reject(
                        context,
                        token_hash,
                        meta,
                        score,
                        components,
                        PolicyDecision("block", 401, "client_id_mismatch"),
                        reasons,
                        started,
                    )
                if not _has_scope(meta, required_scope):
                    return self._reject(
                        context,
                        token_hash,
                        meta,
                        score,
                        components,
                        PolicyDecision("block", 403, "insufficient_scope"),
                        reasons,
                        started,
                    )

                proof = verify_device_proof(self.storage, self.settings, context, meta)
                if not proof.valid:
                    return self._reject(
                        context,
                        token_hash,
                        meta,
                        score,
                        components,
                        PolicyDecision("block", 401, proof.reason_code or "device_proof_invalid"),
                        reasons,
                        started,
                    )

                family = str(meta.get("family_id") or token_hash)
                replay = check_replay(
                    self.storage, self.settings, family, context, transactional=transactional
                )
                if replay.detected:
                    reasons.append(replay.reason_code or "replay_detected")
                    return self._reject(
                        context,
                        token_hash,
                        meta,
                        score,
                        components,
                        PolicyDecision("block", 409, replay.reason_code or "replay_detected"),
                        reasons,
                        started,
                        replay_flag=True,
                    )

                count = self.storage.incr_with_ttl(
                    f"rate_limit:{family}:{context.endpoint}", self.settings.burst_window_seconds
                )
                if count > self.settings.burst_hard_limit:
                    reasons.append("rate_limit_exceeded")
                    return self._reject(
                        context,
                        token_hash,
                        meta,
                        score,
                        components,
                        PolicyDecision("block", 429, "rate_limit_exceeded"),
                        reasons,
                        started,
                        request_count=count,
                    )

                ttl = _ttl(meta)
                if self.mode in {"standard", "baseline"}:
                    response = view_func(*args, **kwargs)
                    record_token_use(self.storage, token_hash, meta, ttl)
                    self._log(
                        context,
                        token_hash,
                        meta,
                        1.0,
                        {},
                        "allow",
                        "standard_controls_passed",
                        False,
                        started,
                        reasons,
                        count,
                    )
                    return self._decorate_allowed_response(
                        response,
                        "allow",
                        "standard_controls_passed",
                        1.0,
                        request_count=count,
                    )

                result = compute_trust_score(
                    self.storage,
                    self.settings,
                    family,
                    context,
                    max(ttl, self.settings.registry_ttl_seconds),
                    False,
                    token_metadata=meta,
                    request_count=count,
                )
                score, components = result.trust_score, result.components
                reasons.extend(result.reason_codes)
                critical = (
                    "request_frequency_high"
                    if self.settings.hard_burst_block and "request_frequency_high" in result.reason_codes
                    else None
                )
                decision = decide(self.settings, score, critical)
                if decision.decision == "allow":
                    response = view_func(*args, **kwargs)
                    record_token_use(self.storage, token_hash, meta, ttl)
                    record_context_history(
                        self.storage,
                        family,
                        context,
                        max(ttl, self.settings.registry_ttl_seconds),
                    )
                    self._log(
                        context,
                        token_hash,
                        meta,
                        score,
                        components,
                        "allow",
                        decision.reason_code,
                        False,
                        started,
                        reasons,
                        count,
                    )
                    return self._decorate_allowed_response(
                        response,
                        "allow",
                        decision.reason_code,
                        score,
                        request_count=count,
                    )
                return self._reject(
                    context,
                    token_hash,
                    meta,
                    score,
                    components,
                    decision,
                    reasons,
                    started,
                    request_count=count,
                )

            return wrapper

        return decorator

    def _decorate_allowed_response(
        self,
        response,
        decision: str,
        reason: str,
        score: float,
        *,
        request_count: int | None = None,
    ):
        flask_response = make_response(response)
        if self.settings.experiment_mode:
            flask_response.headers["X-RATF-Decision"] = decision
            flask_response.headers["X-RATF-Reason"] = reason
            flask_response.headers["X-RATF-Score"] = str(score)
            flask_response.headers["X-RATF-Config-Fingerprint"] = self.settings.fingerprint()
            flask_response.headers["X-RATF-Shared-Fingerprint"] = self.settings.shared_experiment_fingerprint()
            if request_count is not None:
                flask_response.headers["X-RATF-Request-Count"] = str(request_count)
        return flask_response

    def _reject(
        self,
        context,
        token_hash,
        meta,
        score,
        components,
        decision,
        reasons,
        started,
        replay_flag=False,
        request_count=None,
    ):
        self._log(
            context,
            token_hash,
            meta,
            score,
            components,
            decision.decision,
            decision.reason_code,
            replay_flag,
            started,
            reasons,
            request_count,
        )
        body = {
            "status": "rejected" if decision.decision == "block" else "verification_required",
            "decision": decision.decision,
            "reason_code": decision.reason_code,
            "trust_score": score,
            "request_id": context.request_id,
        }
        response = jsonify(body)
        response.status_code = decision.http_status
        response.headers["Cache-Control"] = "no-store"
        if decision.decision == "verify":
            body["message"] = "Reauthentication or step-up verification required"
            response = jsonify(body)
            response.status_code = decision.http_status
            response.headers["WWW-Authenticate"] = 'Bearer error="insufficient_user_authentication"'
            response.headers["Cache-Control"] = "no-store"
        if self.settings.experiment_mode:
            response.headers["X-RATF-Decision"] = decision.decision
            response.headers["X-RATF-Reason"] = decision.reason_code
            if score is not None:
                response.headers["X-RATF-Score"] = str(score)
            response.headers["X-RATF-Config-Fingerprint"] = self.settings.fingerprint()
            response.headers["X-RATF-Shared-Fingerprint"] = self.settings.shared_experiment_fingerprint()
            if request_count is not None:
                response.headers["X-RATF-Request-Count"] = str(request_count)
        return response

    def _context_for_log(self, value: str | None) -> str | None:
        if not value:
            return None
        if self.settings.log_context_mode == "raw":
            return value
        digest = hmac.new(
            self.settings.token_hash_secret.encode(), value.encode(), hashlib.sha256
        ).hexdigest()
        if self.settings.log_context_mode == "masked":
            return digest[:12]
        return digest

    def _log(
        self,
        context,
        token_hash,
        meta,
        score,
        components,
        decision,
        reason,
        replay_flag,
        started,
        reasons,
        request_count,
    ):
        self.audit_logger.write(
            {
                "schema_version": "2.0",
                "config_fingerprint": self.settings.fingerprint(),
                "shared_experiment_fingerprint": self.settings.shared_experiment_fingerprint(),
                "system_mode": self.mode,
                "storage_backend": self.storage.backend_name,
                "request_id": context.request_id,
                "run_id": context.run_id,
                "scenario_label": context.scenario_label,
                "timestamp": context.timestamp,
                "request_timestamp": context.request_timestamp,
                "token_id_hash": token_hash,
                "token_format": meta.get("token_format"),
                "token_family_id_hash": self._context_for_log(meta.get("family_id")),
                "subject_hash": self._context_for_log(meta.get("sub")),
                "client_id": context.client_id,
                "device_id_hash": self._context_for_log(context.device_id),
                "source_ip_hash": self._context_for_log(context.source_ip),
                "user_agent_hash": self._context_for_log(context.user_agent),
                "endpoint": context.endpoint,
                "method": context.method,
                "body_hash": context.body_hash,
                "idempotency_key_hash": self._context_for_log(context.idempotency_key),
                "nonce_hash": self._context_for_log(context.nonce),
                "trust_score": score,
                "score_components": components,
                "request_count_window": request_count,
                "decision": decision,
                "reason_code": reason,
                "reason_codes": sorted(set(reasons)),
                "latency_ms": round((time.perf_counter() - started) * 1000, 4),
                "replay_flag": replay_flag,
                "experiment_headers_accepted": context.experiment_headers_accepted,
            }
        )
