from __future__ import annotations

import hashlib
import hmac
import time
from collections import deque
from datetime import datetime, timezone
from typing import Any, Callable

from ..device_proof import verify_device_proof
from ..policy import decide
from ..replay import check_replay
from ..storage import Storage
from ..trust_score import compute_trust_score, record_context_history
from .config import CoreConfig
from .models import (
    EvaluationRequest,
    EvaluationResult,
    Identity,
    RequestContext,
)
from .ports import IdentityProvider, StepUpHandler


class RATFEngine:
    """Transport-independent implementation of the R-ATF decision flow."""

    def __init__(
        self,
        config: CoreConfig,
        storage: Storage,
        *,
        identity_provider: IdentityProvider | None = None,
        step_up_handler: StepUpHandler | None = None,
        event_handler: Callable[[dict[str, Any]], None] | None = None,
        event_limit: int = 200,
    ):
        config.validate()
        self.config = config
        self.storage = storage
        self.identity_provider = identity_provider
        self.step_up_handler = step_up_handler
        self.event_handler = event_handler
        self._events: deque[dict[str, Any]] = deque(maxlen=max(10, event_limit))

    def evaluate_token(self, access_token: str | None, evaluation: EvaluationRequest) -> EvaluationResult:
        policy_name = evaluation.policy.name if evaluation.policy else "default"
        if not access_token:
            return self._reject(
                evaluation.context,
                "missing_bearer_token",
                401,
                policy_name=policy_name,
            )
        if self.identity_provider is None:
            return self._reject(
                evaluation.context,
                "identity_provider_not_configured",
                500,
                policy_name=policy_name,
            )
        authentication = self.identity_provider.authenticate(access_token, evaluation.context)
        if not authentication.valid or authentication.identity is None:
            return self._reject(
                evaluation.context,
                authentication.reason_code or "invalid_token",
                401,
                policy_name=policy_name,
            )
        return self.evaluate_identity(authentication.identity, evaluation)

    def evaluate_identity(self, identity: Identity, evaluation: EvaluationRequest) -> EvaluationResult:
        started = time.perf_counter()
        context = evaluation.context
        config = evaluation.policy.resolve(self.config) if evaluation.policy else self.config
        policy_name = evaluation.policy.name if evaluation.policy else "default"
        if not identity.subject:
            return self._reject(
                context,
                "subject_missing",
                401,
                started=started,
                policy_name=policy_name,
            )
        if context.client_id and identity.client_id and context.client_id != identity.client_id:
            return self._reject(
                context,
                "client_id_mismatch",
                401,
                started=started,
                policy_name=policy_name,
            )
        if not identity.has_scope(evaluation.required_scope):
            return self._reject(
                context,
                "insufficient_scope",
                403,
                started=started,
                policy_name=policy_name,
            )

        if evaluation.enforce_request_integrity:
            proof = verify_device_proof(self.storage, config, context, identity.metadata)
            if not proof.valid:
                return self._reject(
                    context,
                    proof.reason_code or "device_proof_invalid",
                    401,
                    started=started,
                    policy_name=policy_name,
                )
            replay = check_replay(
                self.storage,
                config,
                identity.family_id,
                context,
                transactional=evaluation.transactional,
            )
            if replay.detected:
                return self._reject(
                    context,
                    replay.reason_code or "replay_detected",
                    409,
                    reason_codes=[replay.reason_code or "replay_detected"],
                    started=started,
                    policy_name=policy_name,
                )

        request_count = evaluation.request_count
        if request_count is None:
            request_count = self.storage.incr_with_ttl(
                f"rate_limit:{identity.family_id}:{context.endpoint}",
                config.burst_window_seconds,
            )
        if request_count > config.burst_hard_limit:
            return self._reject(
                context,
                "rate_limit_exceeded",
                429,
                request_count=request_count,
                reason_codes=["rate_limit_exceeded"],
                started=started,
                policy_name=policy_name,
            )

        ttl = self._identity_ttl(identity)
        score = compute_trust_score(
            self.storage,
            config,
            identity.family_id,
            context,
            max(ttl, config.registry_ttl_seconds),
            False,
            token_metadata=identity.metadata,
            request_count=request_count,
        )
        critical = (
            "request_frequency_high"
            if config.hard_burst_block and "request_frequency_high" in score.reason_codes
            else None
        )
        policy = decide(config, score.trust_score, critical)
        shadowed = config.shadow_mode and policy.decision != "allow"
        effective_decision = "allow" if shadowed else policy.decision
        http_status = 200 if shadowed else policy.http_status
        result = EvaluationResult(
            decision=policy.decision,
            effective_decision=effective_decision,
            http_status=http_status,
            reason_code=policy.reason_code,
            request_id=context.request_id,
            trust_score=score.trust_score,
            components=score.components,
            reason_codes=score.reason_codes,
            request_count=request_count,
            shadow_mode=shadowed,
            policy_name=policy_name,
        )
        if policy.decision == "verify" and self.step_up_handler:
            result.step_up = self.step_up_handler.create_challenge(context, identity, result)

        should_learn = policy.decision == "allow" or (shadowed and config.learn_in_shadow)
        if should_learn:
            record_context_history(
                self.storage,
                identity.family_id,
                context,
                max(ttl, config.registry_ttl_seconds),
            )
        if result.allowed and self.identity_provider:
            self.identity_provider.record_use(identity, ttl)
        self._emit(result, context, identity=identity, started=started)
        return result

    def recent_events(self, limit: int = 50) -> list[dict[str, Any]]:
        return list(self._events)[-max(1, min(limit, len(self._events) or 1)) :]

    def reset(self) -> None:
        self.storage.clear()
        self._events.clear()

    @staticmethod
    def _identity_ttl(identity: Identity) -> int:
        if identity.expires_at is None:
            return 900
        return max(identity.expires_at - int(time.time()), 1)

    def _reject(
        self,
        context: RequestContext,
        reason: str,
        status: int,
        *,
        request_count: int | None = None,
        reason_codes: list[str] | None = None,
        started: float | None = None,
        policy_name: str = "default",
    ) -> EvaluationResult:
        decision = "verify" if reason == "trust_score_verify" else "block"
        result = EvaluationResult(
            decision=decision,
            effective_decision=decision,
            http_status=status,
            reason_code=reason,
            request_id=context.request_id,
            reason_codes=reason_codes or [],
            request_count=request_count,
            policy_name=policy_name,
        )
        self._emit(result, context, started=started)
        return result

    def _emit(
        self,
        result: EvaluationResult,
        context: RequestContext,
        *,
        identity: Identity | None = None,
        started: float | None = None,
    ) -> None:
        finished = time.perf_counter()
        started = finished if started is None else started
        subject_hash = None
        if identity and identity.subject:
            subject_hash = hmac.new(
                self.config.token_hash_secret.encode(),
                identity.subject.encode(),
                hashlib.sha256,
            ).hexdigest()
        event = {
            "schema_version": "3.0",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "request_id": context.request_id,
            "run_id": context.run_id,
            "scenario_label": context.scenario_label,
            "subject_hash": subject_hash,
            "client_id": context.client_id,
            "endpoint": context.endpoint,
            "method": context.method,
            "decision": result.decision,
            "effective_decision": result.effective_decision,
            "reason_code": result.reason_code,
            "reason_codes": result.reason_codes,
            "trust_score": result.trust_score,
            "score_components": result.components,
            "request_count_window": result.request_count,
            "shadow_mode": result.shadow_mode,
            "step_up": result.step_up.to_dict() if result.step_up else None,
            "policy_name": result.policy_name,
            "latency_ms": round((finished - started) * 1000, 4),
        }
        self._events.append(event)
        if self.event_handler:
            self.event_handler(dict(event))
