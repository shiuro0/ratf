from __future__ import annotations

import uuid
from typing import Any

from flask import Flask, jsonify, request

from ratf.auth import introspect_token, issue_access_token, revoke_token
from ratf.config import Settings
from ratf.context import extract_issuance_context
from ratf.device_proof import authenticate_device, get_device, register_device
from ratf.logging_utils import AuditLogger
from ratf.middleware import SecurityMiddleware
from ratf.storage import create_storage
from ratf.validation import validate_order, validate_payment


def _payload() -> dict[str, Any]:
    value = request.get_json(silent=True)
    return value if isinstance(value, dict) else {}


def create_app(settings: Settings | None = None) -> Flask:
    settings = settings or Settings()
    if settings.strict_startup:
        settings.assert_valid()
    storage = create_storage(settings)
    logger = AuditLogger(settings.log_path, settings.audit_log_secret)
    security = SecurityMiddleware(settings, storage, logger, settings.api_mode)
    app = Flask(__name__)
    app.config.update(
        SETTINGS=settings,
        STORAGE=storage,
        AUDIT_LOGGER=logger,
        MAX_CONTENT_LENGTH=settings.max_request_body_bytes,
    )

    def admin_ok() -> bool:
        return request.headers.get("X-Admin-Token") == settings.admin_token

    def enrollment_ok() -> bool:
        return admin_ok() or request.headers.get("X-Enrollment-Key") == settings.device_enrollment_key

    def resource_ok() -> bool:
        return request.headers.get("X-Resource-Server-Key") == settings.resource_server_key or admin_ok()

    @app.after_request
    def secure_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        if request.path.startswith(("/auth/", "/oauth/", "/admin/")):
            response.headers.setdefault("Cache-Control", "no-store")
        return response

    @app.errorhandler(413)
    def request_too_large(_error):
        return jsonify({"error": "request_body_too_large"}), 413

    @app.errorhandler(500)
    def internal_error(_error):
        return jsonify({"error": "internal_server_error"}), 500

    @app.get("/health")
    def health():
        report = settings.validation_report()
        storage_ok = storage.ping()
        response = jsonify(
            {
                "status": "ok" if storage_ok else "degraded",
                "mode": settings.api_mode,
                "storage_backend": storage.backend_name,
                "config_fingerprint": settings.fingerprint(),
                "shared_experiment_fingerprint": settings.shared_experiment_fingerprint(),
                "configuration_warnings": report["warnings"],
                "controls": {
                    "token_registry": True,
                    "access_token_replacement": settings.replace_previous_access_token,
                    "nonce": settings.nonce_required,
                    "device_proof": settings.device_proof_required,
                    "idempotency": settings.idempotency_required,
                    "rate_limit": True,
                    "trust_score": settings.api_mode == "ratf",
                    "audit_hash_chain": True,
                },
            }
        )
        # A degraded dependency must not be reported as a successful Docker
        # health check. The process remains alive so its diagnostics are still
        # reachable, but Compose will not send experiments to it as healthy.
        return response, 200 if storage_ok else 503

    @app.post("/auth/device/register")
    def device_register():
        if not enrollment_ok():
            return jsonify({"error": "device_enrollment_authorization_required"}), 401
        p = _payload()
        user_id = str(p.get("user_id", "")).strip()
        client_id = str(p.get("client_id", "")).strip()
        if not user_id or not client_id:
            return jsonify({"error": "user_id_and_client_id_required"}), 400
        result = register_device(
            storage,
            settings,
            user_id=user_id,
            client_id=client_id,
            device_name=str(p.get("device_name", "Research Device"))[:100],
            role=str(p.get("role", "customer"))[:32],
            allowed_scopes=p.get("allowed_scopes")
            or "catalog:read orders:read orders:write payments:write",
            device_id=p.get("device_id"),
        )
        return (
            jsonify(
                {
                    **result,
                    "warning": "The device secret is shown only to support the local experiment. It is not stored in plaintext in Redis.",
                }
            ),
            201,
        )

    @app.post("/oauth/token")
    def oauth_token():
        p = _payload()
        user_id = str(p.get("user_id", "")).strip()
        client_id = str(p.get("client_id", "")).strip()
        device_id = str(p.get("device_id", "")).strip()
        secret = str(p.get("device_secret", ""))
        if not user_id or not client_id or not device_id or not secret:
            return jsonify({"error": "device_credentials_required"}), 400
        if not authenticate_device(storage, settings, device_id, secret, user_id, client_id):
            return jsonify({"error": "invalid_device_credentials"}), 401
        device = get_device(storage, device_id) or {}
        try:
            token = issue_access_token(
                user_id=user_id,
                role=str(device.get("role", "customer")),
                client_id=client_id,
                device_id=device_id,
                settings=settings,
                storage=storage,
                token_format=str(p.get("token_format", "jwt")),
                scope=p.get("scope"),
                allowed_scopes=device.get("allowed_scopes", []),
                ttl_seconds=int(p["ttl_seconds"]) if p.get("ttl_seconds") is not None else None,
                # Family identifiers are server-derived by default. A supplied value
                # is accepted only for controlled experiments using the experiment key.
                family_id=p.get("family_id")
                if request.headers.get("X-Experiment-Key") == settings.experiment_key
                else None,
                rotate_family=None,
                issuance_context=extract_issuance_context(request, settings),
            )
        except (TypeError, ValueError) as exc:
            return jsonify({"error": "invalid_token_request", "error_description": str(exc)}), 400
        return jsonify(
            {
                **token,
                "prototype_note": "This endpoint is a local token-issuer simulation, not a complete OAuth authorization server.",
            }
        )

    @app.post("/auth/login")
    def research_bootstrap_login():
        """Convenience endpoint for local tools; guarded by the enrollment key."""
        if not enrollment_ok():
            return jsonify({"error": "device_enrollment_authorization_required"}), 401
        p = _payload()
        user_id = str(p.get("user_id", "user_001"))
        client_id = str(p.get("client_id", "research-client"))
        device = register_device(
            storage,
            settings,
            user_id=user_id,
            client_id=client_id,
            device_name=str(p.get("device_name", "Research Bootstrap Device")),
            role="customer",
            allowed_scopes=p.get("allowed_scopes")
            or "catalog:read orders:read orders:write payments:write",
        )
        token = issue_access_token(
            user_id=user_id,
            role="customer",
            client_id=client_id,
            device_id=device["device_id"],
            settings=settings,
            storage=storage,
            token_format=str(p.get("token_format", "jwt")),
            scope=p.get("scope"),
            allowed_scopes=device["allowed_scopes"],
            ttl_seconds=int(p["ttl_seconds"]) if p.get("ttl_seconds") is not None else None,
            issuance_context=extract_issuance_context(request, settings),
        )
        return jsonify(
            {
                **token,
                **device,
                "compatibility_endpoint": True,
                "warning": "This endpoint bootstraps a synthetic identity and is not a production password login.",
            }
        )

    @app.post("/oauth/introspect")
    def introspect():
        if not resource_ok():
            return jsonify({"error": "resource_server_authentication_required"}), 401
        return jsonify(introspect_token(str(_payload().get("token", "")), settings, storage))

    @app.post("/oauth/revoke")
    def revoke():
        if not admin_ok():
            return jsonify({"error": "admin_token_required"}), 401
        p = _payload()
        return jsonify(
            {
                "revoked": revoke_token(
                    str(p.get("token", "")),
                    settings,
                    storage,
                    str(p.get("reason", "manual_revocation")),
                )
            }
        )

    @app.get("/api/v1/catalog/products")
    @security.protect(required_scope="catalog:read")
    def products():
        return jsonify(
            {
                "items": [
                    {"sku": "SKU-RED-01", "name": "Tas Merah", "price": 175000, "stock": 12},
                    {"sku": "SKU-BLK-02", "name": "Dompet Hitam", "price": 95000, "stock": 24},
                ]
            }
        )

    @app.post("/api/v1/orders")
    @security.protect(required_scope="orders:write", transactional=True)
    def create_order():
        p = _payload()
        check = validate_order(p)
        if not check.valid:
            return jsonify({"error": "invalid_order_payload", "details": check.errors}), 422
        order_id = f"ord_{uuid.uuid4().hex[:12]}"
        order = {
            "order_id": order_id,
            "customer_id": p["customer_id"],
            "items": p["items"],
            "shipping_method": p.get("shipping_method", "regular"),
            "status": "created",
        }
        storage.set_json(f"order:{order_id}", order, ttl_seconds=3600)
        return jsonify(order), 201

    @app.get("/api/v1/orders/<order_id>")
    @security.protect(required_scope="orders:read")
    def get_order(order_id: str):
        order = storage.get_json(f"order:{order_id}")
        return (jsonify(order), 200) if order else (jsonify({"error": "order_not_found"}), 404)

    @app.post("/api/v1/payments/charge")
    @security.protect(required_scope="payments:write", transactional=True)
    def payment():
        p = _payload()
        check = validate_payment(p, settings.max_payment_amount)
        if not check.valid:
            return jsonify({"error": "invalid_payment_payload", "details": check.errors}), 422
        if not storage.get_json(f"order:{p['order_id']}"):
            return jsonify({"error": "order_not_found"}), 404
        return (
            jsonify(
                {
                    "payment_id": f"pay_{uuid.uuid4().hex[:12]}",
                    "order_id": p["order_id"],
                    "amount": p["amount"],
                    "currency": p.get("currency", "IDR"),
                    "payment_method": p.get("payment_method", "virtual_account"),
                    "status": "authorized",
                }
            ),
            201,
        )

    @app.get("/api/resource")
    @security.protect(required_scope="catalog:read")
    def resource():
        return jsonify({"status": "ok", "resource": "protected-profile", "mode": settings.api_mode})

    @app.post("/api/transaction")
    @security.protect(required_scope="orders:write", transactional=True)
    def transaction():
        return jsonify({"status": "ok", "transaction": _payload(), "mode": settings.api_mode})

    @app.get("/admin/config")
    def config_snapshot():
        if not admin_ok():
            return jsonify({"error": "admin_token_required"}), 401
        return jsonify(
            {
                "config": settings.public_config(),
                "config_fingerprint": settings.fingerprint(),
                "shared_experiment_fingerprint": settings.shared_experiment_fingerprint(),
                "validation": settings.validation_report(),
                "storage_backend": storage.backend_name,
            }
        )

    @app.get("/admin/logs")
    def logs():
        if not admin_ok():
            return jsonify({"error": "admin_token_required"}), 401
        limit = max(1, min(int(request.args.get("limit", 100)), 1000))
        return jsonify(logger.read_recent(limit))

    @app.get("/admin/audit/verify")
    def verify_audit():
        if not admin_ok():
            return jsonify({"error": "admin_token_required"}), 401
        return jsonify(logger.verify_integrity())

    @app.post("/admin/reset")
    def reset():
        if not admin_ok():
            return jsonify({"error": "admin_token_required"}), 401
        storage.clear()
        logger.clear()
        return jsonify({"status": "reset_ok", "mode": settings.api_mode})

    return app


if __name__ == "__main__":
    current = Settings()
    create_app().run(host=current.host, port=current.port, debug=False)
