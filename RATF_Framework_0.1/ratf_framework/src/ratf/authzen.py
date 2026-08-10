from __future__ import annotations

import hashlib
import hmac
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Callable

from flask import Blueprint, jsonify, request

from .core.engine import RATFEngine
from .core.models import EvaluationRequest, Identity, RequestContext
from .core.profile import PolicyProfile


def _properties(entity: Any) -> dict[str, Any]:
    if not isinstance(entity, dict):
        return {}
    value = entity.get("properties", {})
    return value if isinstance(value, dict) else {}


def _scopes(value: Any) -> tuple[str, ...]:
    if isinstance(value, list):
        return tuple(sorted({str(item) for item in value if str(item)}))
    return tuple(sorted({item for item in str(value or "").split() if item}))


def _context_from_payload(payload: dict[str, Any], request_id: str) -> RequestContext:
    subject = payload["subject"]
    resource = payload["resource"]
    action = payload["action"]
    supplied = payload.get("context") or {}
    supplied = supplied if isinstance(supplied, dict) else {}
    context_values = _properties(supplied) or supplied
    subject_values = _properties(subject)
    resource_values = _properties(resource)
    action_values = _properties(action)
    now = datetime.now(timezone.utc)
    hour = int(context_values.get("hour_utc", now.hour)) % 24
    method = str(action_values.get("method") or action.get("name") or action.get("id") or "GET")
    endpoint = str(resource_values.get("path") or resource.get("id") or "/")
    body_hash = str(context_values.get("body_hash") or hashlib.sha256(b"{}").hexdigest())
    fingerprint_material = json.dumps(
        [method, endpoint, body_hash, request_id], separators=(",", ":")
    ).encode()
    return RequestContext(
        request_id=request_id,
        run_id=str(context_values.get("run_id", "authzen")),
        scenario_label=str(context_values.get("scenario_label", "external_evaluation")),
        source_ip=str(context_values.get("source_ip", "unknown")),
        user_agent=str(context_values.get("user_agent", "unknown")),
        client_id=str(context_values.get("client_id") or subject_values.get("client_id") or ""),
        device_id=str(context_values.get("device_id", "")),
        method=method.upper(),
        endpoint=endpoint,
        timestamp=now.isoformat(),
        request_timestamp=None,
        hour_utc=hour,
        body_hash=body_hash,
        request_fingerprint=hashlib.sha256(fingerprint_material).hexdigest(),
        nonce=None,
        idempotency_key=None,
        device_signature=None,
    )


def create_authzen_blueprint(
    engine: RATFEngine,
    api_key: str,
    *,
    policy_resolver: Callable[[PolicyProfile | str | None], PolicyProfile | None] | None = None,
) -> Blueprint:
    blueprint = Blueprint("ratf_authzen", __name__)

    @blueprint.post("/access/v1/evaluation")
    def access_evaluation():
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        if not api_key:
            return jsonify({"error": "authzen_api_key_not_configured"}), 503
        authorization = request.headers.get("Authorization", "")
        supplied_key = authorization[7:] if authorization.startswith("Bearer ") else ""
        if not supplied_key or not hmac.compare_digest(supplied_key, api_key):
            response = jsonify({"error": "evaluation_service_authentication_required"})
            response.status_code = 401
            response.headers["X-Request-ID"] = request_id
            return response

        payload = request.get_json(silent=True)
        if not isinstance(payload, dict) or not all(
            isinstance(payload.get(name), dict) for name in ("subject", "resource", "action")
        ):
            response = jsonify({"error": "subject_resource_and_action_are_required"})
            response.status_code = 400
            response.headers["X-Request-ID"] = request_id
            return response

        subject_values = _properties(payload["subject"])
        action_values = _properties(payload["action"])
        resource_values = _properties(payload["resource"])
        context_values = _properties(payload.get("context")) or payload.get("context") or {}
        policy_id = context_values.get("policy_id")
        try:
            selected_policy = policy_resolver(policy_id) if policy_resolver else None
        except ValueError as exc:
            response = jsonify({"error": "unknown_policy", "message": str(exc)})
            response.status_code = 400
            response.headers["X-Request-ID"] = request_id
            return response
        identity = Identity(
            subject=str(payload["subject"].get("id") or subject_values.get("sub") or ""),
            client_id=str(subject_values.get("client_id") or context_values.get("client_id") or ""),
            scopes=_scopes(subject_values.get("scopes") or subject_values.get("scope")),
            token_id=str(subject_values.get("token_id") or "authzen-subject"),
            family_id=str(subject_values.get("family_id") or subject_values.get("sid") or payload["subject"].get("id") or "authzen"),
            expires_at=None,
            metadata={
                **subject_values,
                "issued_ip": subject_values.get("issued_ip") or context_values.get("issued_ip"),
                "issued_user_agent": subject_values.get("issued_user_agent") or context_values.get("issued_user_agent"),
                "issued_hour_utc": subject_values.get("issued_hour_utc")
                if subject_values.get("issued_hour_utc") is not None
                else context_values.get("issued_hour_utc"),
            },
        )
        evaluation = engine.evaluate_identity(
            identity,
            EvaluationRequest(
                context=_context_from_payload(payload, request_id),
                required_scope=action_values.get("required_scope"),
                transactional=bool(resource_values.get("transactional", False)),
                enforce_request_integrity=False,
                request_count=int(context_values["request_count"])
                if context_values.get("request_count") is not None
                else None,
                policy=selected_policy,
            ),
        )
        ratf_context = {
            "decision": evaluation.decision,
            "effective_decision": evaluation.effective_decision,
            "reason_code": evaluation.reason_code,
            "reason_codes": evaluation.reason_codes,
            "trust_score": evaluation.trust_score,
            "score_components": evaluation.components,
            "request_count": evaluation.request_count,
            "shadow_mode": evaluation.shadow_mode,
            "step_up": evaluation.step_up.to_dict() if evaluation.step_up else None,
            "policy_name": evaluation.policy_name,
        }
        response = jsonify({"decision": evaluation.allowed, "context": {"ratf": ratf_context}})
        response.headers["X-Request-ID"] = request_id
        return response

    return blueprint
