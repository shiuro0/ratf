from __future__ import annotations

import os
import uuid
from dataclasses import replace

from flask import Flask, jsonify, request

from ratf import RATF
from ratf.config import Settings
from ratf.core import CoreConfig, StepUpChallenge
from ratf.core.ports import CallbackStepUpHandler
from ratf.identity import OIDCIntrospectionIdentityProvider
from ratf.logging_utils import AuditLogger
from ratf.storage import RedisStorage


def required_environment(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Environment variable {name} wajib diisi")
    return value


def create_app() -> Flask:
    settings = replace(
        Settings(),
        app_env="production",
        strict_startup=True,
        experiment_mode=False,
        storage_backend="redis",
        allow_memory_fallback=False,
        redis_url=required_environment("REDIS_URL"),
        token_hash_secret=required_environment("TOKEN_HASH_SECRET"),
        audit_log_secret=required_environment("AUDIT_LOG_SECRET"),
        log_path=os.getenv("LOG_PATH", "results/production_audit.jsonl"),
    )
    core_config = CoreConfig.from_settings(settings)
    # This example uses an OAuth/OIDC access token. Enable device proof only
    # when the real client has a suitable proof mechanism and key lifecycle.
    core_config.device_proof_required = False
    core_config.validate()

    identity_provider = OIDCIntrospectionIdentityProvider(
        introspection_url=required_environment("OIDC_INTROSPECTION_URL"),
        client_id=required_environment("OIDC_CLIENT_ID"),
        client_secret=required_environment("OIDC_CLIENT_SECRET"),
    )

    def create_step_up(context, identity, evaluation):
        return StepUpChallenge(
            challenge_type="mfa",
            challenge_url=f"/auth/step-up?subject={identity.subject}",
            expires_in=180,
            message=f"Verifikasi tambahan diperlukan: {evaluation.reason_code}",
        )

    app = Flask(__name__)
    app.config.update(
        RATF_CORE_CONFIG=core_config,
        RATF_DASHBOARD_ENABLED=False,
        RATF_AUTHZEN_ENABLED=False,
    )
    ratf = RATF(
        settings=settings,
        storage=RedisStorage(settings.redis_url),
        identity_provider=identity_provider,
        step_up_handler=CallbackStepUpHandler(create_step_up),
        audit_logger=AuditLogger(settings.log_path, settings.audit_log_secret),
    )
    payment_policy = ratf.policy(
        "important-payment",
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

    @app.post("/api/payments")
    @ratf.protect(
        required_scope="payments:write",
        transactional=True,
        policy=payment_policy,
    )
    def create_payment():
        payload = request.get_json(silent=True) or {}
        try:
            amount = int(payload.get("amount", 0))
        except (TypeError, ValueError):
            amount = 0
        if amount <= 0:
            return jsonify({"error": "amount_must_be_positive"}), 400
        return (
            jsonify(
                {
                    "payment_id": f"payment_{uuid.uuid4().hex[:12]}",
                    "amount": amount,
                    "status": "accepted",
                }
            ),
            201,
        )

    @app.post("/auth/step-up")
    def step_up_placeholder():
        return jsonify(
            {
                "status": "integration_required",
                "message": "Hubungkan endpoint ini ke MFA milik Identity Provider.",
            }
        ), 501

    return app
