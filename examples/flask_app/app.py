from __future__ import annotations

import os
import sys
import uuid
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from flask import Blueprint, Flask, jsonify, request

from ratf import RATF
from ratf.config import Settings
from ratf.core import CoreConfig, Identity, StepUpChallenge
from ratf.core.ports import CallbackStepUpHandler
from ratf.identity import CallbackIdentityProvider
from ratf.logging_utils import AuditLogger
from ratf.storage import create_storage


TOKENS = {
    "app-token-alice": {
        "sub": "customer-001",
        "client_id": "marketplace-app",
        "scope": "catalog:read orders:write payments:write",
        "family_id": "family-customer-001",
        "issued_ip": "192.168.10.10",
        "issued_user_agent": "MarketplaceApp/1.0",
        "issued_hour_utc": 10,
    }
}


def application_idp(access_token, _context):
    claims = TOKENS.get(access_token)
    if not claims:
        return None
    return {
        "active": True,
        "subject": claims["sub"],
        "client_id": claims["client_id"],
        "scope": claims["scope"],
        "token_id": "token-alice",
        "family_id": claims["family_id"],
        "metadata": claims,
    }


def start_step_up(_context, identity, evaluation):
    return StepUpChallenge(
        challenge_type="reauthentication",
        challenge_url=f"/app/step-up/{identity.subject}",
        expires_in=180,
        message=f"Konfirmasi ulang diperlukan karena {evaluation.reason_code}",
    )


def create_app(*, audit_path: str | None = None) -> Flask:
    use_redis = os.getenv("RATF_EXAMPLE_STORAGE", "memory").lower() == "redis"
    settings = replace(
        Settings(),
        storage_backend="redis" if use_redis else "memory",
        allow_memory_fallback=not use_redis,
        experiment_mode=True,
        experiment_key="local-experiment-key-32-characters-long",
        log_path=audit_path
        or os.getenv(
            "RATF_EXAMPLE_AUDIT_PATH",
            str(ROOT / "instance" / "ratf_example_audit.jsonl"),
        ),
    )
    storage = create_storage(settings)
    policy = CoreConfig.from_settings(settings)
    policy.device_proof_required = False

    app = Flask(__name__)
    app.config.update(
        RATF_CORE_CONFIG=policy,
        RATF_DASHBOARD_ENABLED=True,
        RATF_DASHBOARD_UNSAFE_LOCAL=True,
        RATF_AUTHZEN_ENABLED=True,
        RATF_AUTHZEN_API_KEY="local-authzen-service-key",
    )
    ratf = RATF(
        settings=settings,
        storage=storage,
        identity_provider=CallbackIdentityProvider(application_idp),
        step_up_handler=CallbackStepUpHandler(start_step_up),
        audit_logger=AuditLogger(settings.log_path, settings.audit_log_secret),
    )
    important_api = ratf.policy(
        "important-api",
        weights={
            "ip": 0.30,
            "device": 0.25,
            "time": 0.10,
            "frequency": 0.20,
            "token_history": 0.15,
        },
        thresholds={"verify": 0.70, "allow": 0.88},
        burst_soft_limit=15,
        burst_hard_limit=40,
    )
    ratf.init_app(app)

    @app.get("/")
    def home():
        return jsonify(
            {
                "module": "RATF",
                "dashboard": "/ratf/dashboard/",
                "authzen": "/access/v1/evaluation",
                "local_debug": "/app/debug/ratf",
                "storage": storage.backend_name,
            }
        )

    @app.post("/app/login")
    def login():
        return jsonify(
            {
                "access_token": "app-token-alice",
                "token_type": "Bearer",
                "note": "Token contoh ini diterbitkan oleh aplikasi, bukan oleh R-ATF.",
            }
        )

    @app.post("/api/orders")
    @ratf.protect("orders:write", transactional=True)
    def create_order():
        payload = request.get_json(silent=True) or {}
        return (
            jsonify(
                {
                    "order_id": f"order_{uuid.uuid4().hex[:10]}",
                    "item": payload.get("item", "Produk contoh"),
                    "quantity": int(payload.get("quantity", 1)),
                    "status": "created",
                }
            ),
            201,
        )

    payments_api = Blueprint("payments_api", __name__, url_prefix="/api")

    @payments_api.post("/payments")
    def create_payment():
        payload = request.get_json(silent=True) or {}
        return (
            jsonify(
                {
                    "payment_id": f"payment_{uuid.uuid4().hex[:10]}",
                    "amount": int(payload.get("amount", 100000)),
                    "status": "accepted",
                    "policy": "important-api",
                }
            ),
            201,
        )

    ratf.protect_blueprint(
        payments_api,
        required_scope="payments:write",
        transactional=True,
        policy=important_api,
    )
    app.register_blueprint(payments_api)

    @app.post("/app/step-up/<subject>")
    def step_up(subject: str):
        return jsonify(
            {
                "subject": subject,
                "status": "example_only",
                "message": "Hubungkan endpoint ini ke MFA atau IdP milik aplikasi.",
            }
        )

    @app.get("/app/debug/ratf")
    def debug_ratf():
        expected_key = os.getenv("RATF_EXAMPLE_DEBUG_KEY", "local-debug-key")
        if request.headers.get("X-Debug-Key") != expected_key:
            return jsonify({"message": "Debug key tidak valid"}), 401

        snapshot = ratf.debug_snapshot("family-customer-001", limit=10)
        snapshot["audit_integrity"] = ratf.audit_logger.verify_integrity()
        return jsonify(snapshot)

    return app


if __name__ == "__main__":
    print("R-ATF dashboard: http://127.0.0.1:5100/ratf/dashboard/")
    print("Storage:", os.getenv("RATF_EXAMPLE_STORAGE", "memory"))
    create_app().run(host="127.0.0.1", port=5100, debug=False)
