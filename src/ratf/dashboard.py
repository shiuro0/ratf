from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from importlib.resources import files as resource_files
from pathlib import Path
from typing import Any

from flask import Blueprint, current_app, jsonify, render_template, request

from .core.models import EvaluationRequest, Identity, RequestContext


def _extension():
    return current_app.extensions["ratf"]


def _write_allowed() -> bool:
    if current_app.config.get("RATF_DASHBOARD_UNSAFE_LOCAL"):
        return (request.remote_addr or "") in {"127.0.0.1", "::1", "localhost"}
    expected = str(current_app.config.get("RATF_DASHBOARD_KEY", ""))
    return bool(expected and request.headers.get("X-Dashboard-Key") == expected)


def _request_context(values: dict[str, Any], *, baseline: bool = False) -> RequestContext:
    now = datetime.now(timezone.utc)
    method = str(values.get("method", "POST")).upper()
    endpoint = str(values.get("endpoint", "/api/orders"))
    body_hash = hashlib.sha256(json.dumps(values.get("body", {}), sort_keys=True).encode()).hexdigest()
    request_id = f"dashboard_{uuid.uuid4().hex}"
    fingerprint = hashlib.sha256(f"{method}|{endpoint}|{body_hash}|{request_id}".encode()).hexdigest()
    prefix = "issued_" if baseline else ""
    return RequestContext(
        request_id=request_id,
        run_id="dashboard",
        scenario_label="baseline" if baseline else str(values.get("scenario", "manual")),
        source_ip=str(values.get(f"{prefix}ip") or values.get("ip") or "192.168.10.10"),
        user_agent=str(values.get(f"{prefix}user_agent") or values.get("user_agent") or "MarketplaceApp/1.0"),
        client_id=str(values.get("client_id", "marketplace-app")),
        device_id=str(values.get(f"{prefix}device_id") or values.get("device_id") or "device-primary"),
        method=method,
        endpoint=endpoint,
        timestamp=now.isoformat(),
        request_timestamp=None,
        hour_utc=int(values.get(f"{prefix}hour", values.get("hour", 10))) % 24,
        body_hash=body_hash,
        request_fingerprint=fingerprint,
        nonce=None,
        idempotency_key=None,
        device_signature=None,
    )


def create_dashboard_blueprint() -> Blueprint:
    blueprint = Blueprint(
        "ratf_dashboard",
        __name__,
        url_prefix="/ratf/dashboard",
        template_folder="templates",
    )

    @blueprint.get("/")
    def index():
        return render_template("ratf/dashboard.html")

    @blueprint.get("/api/config")
    def policy_config():
        extension = _extension()
        policy_id = str(request.args.get("policy_id", "")).strip()
        if not policy_id:
            return jsonify(
                {
                    "scope": "default",
                    "policy_name": "default",
                    **extension.engine.config.to_dict(),
                }
            )
        try:
            profile = extension.resolve_policy(policy_id)
        except ValueError as exc:
            return jsonify({"error": "unknown_policy", "message": str(exc)}), 404
        return jsonify(
            {
                "scope": "profile",
                "policy_name": policy_id,
                **profile.resolve(extension.engine.config).to_dict(),
            }
        )

    @blueprint.get("/api/policies")
    def policies():
        extension = _extension()
        return jsonify(
            {
                "default": extension.engine.config.to_dict(),
                "profiles": {
                    name: profile.to_dict(extension.engine.config)
                    for name, profile in sorted(extension.policies.items())
                },
                "recommended": str(
                    current_app.config.get("RATF_DASHBOARD_DEFAULT_POLICY", "")
                ),
            }
        )

    @blueprint.put("/api/config")
    def update_policy():
        if not _write_allowed():
            return jsonify({"error": "dashboard_write_authorization_required"}), 401
        values = request.get_json(silent=True) or {}
        try:
            extension = _extension()
            policy_id = str(values.get("policy_id", "")).strip()
            updates = {
                "weights": values.get("weights"),
                "allow_threshold": values.get("allow_threshold"),
                "verify_threshold": values.get("verify_threshold"),
                "shadow_mode": values.get("shadow_mode"),
            }
            if policy_id:
                profile = extension.update_policy_profile(policy_id, **updates)
                config = {
                    "scope": "profile",
                    "policy_name": policy_id,
                    **profile["resolved"],
                }
            else:
                config = {
                    "scope": "default",
                    "policy_name": "default",
                    **extension.update_policy(**updates),
                }
        except (TypeError, ValueError) as exc:
            return jsonify({"error": "invalid_policy", "message": str(exc)}), 400
        return jsonify(config)

    @blueprint.get("/api/demo-context")
    def demo_context():
        """Expose explicit local-demo credentials to the demonstration UI.

        Raw tokens are intentionally returned only when the application owner
        supplies demo context and dashboard access is authorized.
        """

        if not _write_allowed():
            return jsonify({"error": "dashboard_read_authorization_required"}), 401
        values = current_app.config.get("RATF_DASHBOARD_DEMO_CONTEXT")
        if not isinstance(values, dict):
            return jsonify({"available": False})
        response = jsonify({"available": True, **values})
        response.headers["Cache-Control"] = "no-store"
        return response

    @blueprint.post("/api/evaluate")
    def evaluate():
        if not _write_allowed():
            return jsonify({"error": "dashboard_write_authorization_required"}), 401
        values = request.get_json(silent=True)
        if not isinstance(values, dict):
            return jsonify({"error": "json_object_required"}), 400
        extension = _extension()
        engine = extension.engine
        try:
            selected_policy = extension.resolve_policy(values.get("policy_id") or None)
        except ValueError as exc:
            return jsonify({"error": "unknown_policy", "message": str(exc)}), 400
        if bool(values.get("reset", True)):
            engine.reset()

        scopes = values.get("scopes", "orders:write catalog:read")
        scopes = scopes if isinstance(scopes, list) else str(scopes).split()
        identity = Identity(
            subject=str(values.get("subject", "customer-001")),
            client_id=str(values.get("client_id", "marketplace-app")),
            scopes=tuple(scopes),
            token_id="dashboard-token",
            family_id=str(values.get("family_id", "dashboard-family")),
            metadata={
                "sub": str(values.get("subject", "customer-001")),
                "client_id": str(values.get("client_id", "marketplace-app")),
                "scope": " ".join(scopes),
                "issued_ip": str(values.get("issued_ip", "192.168.10.10")),
                "issued_user_agent": str(values.get("issued_user_agent", "MarketplaceApp/1.0")),
                "issued_hour_utc": int(values.get("issued_hour", 10)) % 24,
            },
        )
        baseline = engine.evaluate_identity(
            identity,
            EvaluationRequest(
                context=_request_context(values, baseline=True),
                required_scope=str(values.get("required_scope", "orders:write")),
                enforce_request_integrity=False,
                request_count=1,
                policy=selected_policy,
            ),
        )
        result = engine.evaluate_identity(
            identity,
            EvaluationRequest(
                context=_request_context(values),
                required_scope=str(values.get("required_scope", "orders:write")),
                transactional=bool(values.get("transactional", True)),
                enforce_request_integrity=False,
                request_count=int(values.get("request_count", 2)),
                policy=selected_policy,
            ),
        )
        return jsonify(
            {
                "baseline": baseline.to_dict(),
                "result": result.to_dict(),
                "policy": (
                    selected_policy.resolve(engine.config).to_dict()
                    if selected_policy is not None
                    else engine.config.to_dict()
                ),
                "explanation": (
                    "Request tetap diteruskan karena shadow mode aktif."
                    if result.shadow_mode
                    else "Keputusan ini diberlakukan pada request."
                ),
            }
        )

    @blueprint.get("/api/events")
    def events():
        return jsonify(_extension().engine.recent_events(50))

    @blueprint.get("/api/research-summary")
    def research_summary():
        configured = str(current_app.config.get("RATF_RESEARCH_RESULTS_DIR", "")).strip()
        if not configured:
            packaged = resource_files("ratf").joinpath("data/research_summary.json")
            if not packaged.is_file():
                return jsonify({"available": False})
            return jsonify(json.loads(packaged.read_text(encoding="utf-8")))
        root = Path(configured)
        security_path = root / "security" / "system_comparison.json"
        validation_path = root / "security" / "final_validation_report.json"
        performance_path = root / "performance" / "performance_comparison.json"
        if not all(path.is_file() for path in (security_path, validation_path, performance_path)):
            packaged = resource_files("ratf").joinpath("data/research_summary.json")
            if not packaged.is_file():
                return jsonify({"available": False, "reason": "research_result_files_incomplete"})
            return jsonify(json.loads(packaged.read_text(encoding="utf-8")))
        security = json.loads(security_path.read_text(encoding="utf-8"))
        validation = json.loads(validation_path.read_text(encoding="utf-8"))
        performance = json.loads(performance_path.read_text(encoding="utf-8"))
        standard = security["standard_mode"]
        ratf = security["ratf_mode"]
        comparisons = performance["comparisons"]
        return jsonify(
            {
                "available": True,
                "security_rows": standard["total_rows_including_setup"] + ratf["total_rows_including_setup"],
                "measured_runs": len(comparisons) * 2 * int(performance["expected_repetitions"]),
                "standard_prevention_percent": standard["Overall attack prevention or challenge rate (%)"],
                "ratf_prevention_percent": ratf["Overall attack prevention or challenge rate (%)"],
                "contextual_requests_improved": standard["FN"] - ratf["FN"],
                "legitimate_requests": ratf["TN"],
                "legitimate_friction_percent": ratf["Legitimate friction rate - blocked or verify (%)"],
                "max_p95_overhead_percent": round(max(item["p95_overhead_percent"] for item in comparisons), 4),
                "largest_throughput_decrease_percent": round(
                    abs(min(item["throughput_delta_percent"] for item in comparisons)), 4
                ),
                "max_failure_rate_percent": round(
                    max(
                        max(item["standard_failure_rate"], item["ratf_failure_rate"])
                        for item in comparisons
                    )
                    * 100,
                    4,
                ),
                "security_quality_passed": bool(validation.get("passed")),
                "performance_quality_passed": bool(performance.get("data_quality_passed")),
                "performance_criteria_passed": bool(performance.get("criteria_passed")),
                "source": "results/research_final",
            }
        )

    return blueprint
