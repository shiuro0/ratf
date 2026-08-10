from __future__ import annotations

import importlib.util
import os
import threading
import uuid
import webbrowser
from dataclasses import replace
from importlib.metadata import PackageNotFoundError, distribution
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, render_template, request

from . import __version__
from .config import Settings
from .core import CoreConfig, StepUpChallenge
from .core.ports import CallbackStepUpHandler
from .flask_extension import RATF
from .identity import CallbackIdentityProvider
from .logging_utils import AuditLogger
from .storage import Storage, create_storage


DEMO_TOKEN = "nusamart-demo-access-token"
DEMO_FAMILY = "nusamart-customer-family"
DEMO_EXPERIMENT_KEY = "nusamart-local-context-key-32-bytes"


def _package_location() -> str:
    try:
        return str(Path(distribution("ratf-framework").locate_file("")).resolve())
    except PackageNotFoundError:
        return str(Path(__file__).resolve().parents[2])


def _identity_provider(access_token, _context):
    if access_token != DEMO_TOKEN:
        return None
    return {
        "active": True,
        "subject": "customer-nusamart-001",
        "client_id": "nusamart-web",
        "scope": "catalog:read orders:write",
        "token_id": "nusamart-demo-token-id",
        "family_id": DEMO_FAMILY,
        "metadata": {
            "sub": "customer-nusamart-001",
            "client_id": "nusamart-web",
            "scope": "catalog:read orders:write",
            "issued_ip": "192.168.10.10",
            "issued_hour_utc": 10,
            "token_source": "application_identity_provider",
        },
    }


def _step_up(_context, identity, evaluation):
    return StepUpChallenge(
        challenge_type="one_time_password",
        challenge_url="/account/verification",
        expires_in=180,
        message="Konfirmasi identitas diperlukan sebelum pesanan diproses.",
        metadata={
            "subject": identity.subject,
            "trigger": evaluation.reason_code,
            "owner": "NusaMart Identity Provider",
        },
    )


def _local_request() -> bool:
    return (request.remote_addr or "") in {"127.0.0.1", "::1", "localhost"}


def create_showcase_app(
    *,
    storage: Storage | None = None,
    audit_path: str | None = None,
) -> Flask:
    selected_backend = os.getenv("RATF_SHOWCASE_STORAGE", "memory").strip().lower()
    if selected_backend not in {"memory", "redis"}:
        raise ValueError("RATF_SHOWCASE_STORAGE harus bernilai memory atau redis")

    log_path = audit_path or os.getenv(
        "RATF_SHOWCASE_AUDIT_PATH",
        str(Path.cwd() / "ratf_showcase_audit.jsonl"),
    )
    settings = replace(
        Settings(),
        app_env="showcase",
        storage_backend=selected_backend,
        redis_url=os.getenv(
            "RATF_SHOWCASE_REDIS_URL",
            os.getenv("REDIS_URL", "redis://localhost:6379/15"),
        ),
        allow_memory_fallback=False,
        experiment_mode=True,
        experiment_key=DEMO_EXPERIMENT_KEY,
        log_path=log_path,
        token_hash_secret="nusamart-local-token-hash-secret",
        audit_log_secret="nusamart-local-audit-chain-secret",
    )
    selected_storage = storage or create_storage(settings)
    core_config = CoreConfig.from_settings(settings)
    core_config.device_proof_required = False

    app = Flask(__name__)
    app.config.update(
        RATF_CORE_CONFIG=core_config,
        RATF_DASHBOARD_ENABLED=True,
        RATF_DASHBOARD_UNSAFE_LOCAL=True,
        RATF_AUTHZEN_ENABLED=True,
        RATF_AUTHZEN_API_KEY="nusamart-local-authzen-key",
        RATF_RESEARCH_RESULTS_DIR=os.getenv("RATF_RESEARCH_RESULTS_DIR", ""),
    )
    audit_logger = AuditLogger(settings.log_path, settings.audit_log_secret)
    ratf = RATF(
        settings=settings,
        storage=selected_storage,
        identity_provider=CallbackIdentityProvider(_identity_provider),
        step_up_handler=CallbackStepUpHandler(_step_up),
        audit_logger=audit_logger,
    )
    checkout_policy = ratf.policy(
        "nusamart-checkout",
        weights={
            "ip": 0.25,
            "device": 0.20,
            "time": 0.10,
            "frequency": 0.20,
            "token_history": 0.25,
        },
        thresholds={"verify": 0.62, "allow": 0.82},
    )
    ratf.init_app(app)

    @app.get("/")
    def storefront():
        return render_template(
            "ratf/showcase.html",
            framework_version=__version__,
            storage_backend=selected_storage.backend_name,
        )

    @app.get("/app/api/bootstrap")
    def bootstrap():
        return jsonify(
            {
                "application": {
                    "name": "NusaMart",
                    "owner": "Aplikasi contoh milik pengembang pengguna R-ATF",
                    "endpoint": "/api/store/orders",
                },
                "framework": {
                    "distribution": "ratf-framework",
                    "version": __version__,
                    "loaded_from": _package_location(),
                    "policy": ratf.policy_config("nusamart-checkout"),
                    "storage": selected_storage.backend_name,
                },
                "client": {
                    "access_token": DEMO_TOKEN,
                    "client_id": "nusamart-web",
                    "device_id": "browser-customer-001",
                    "normal_ip": "192.168.10.10",
                    "normal_hour": 10,
                    "experiment_key": DEMO_EXPERIMENT_KEY,
                },
            }
        )

    @app.post("/api/store/orders")
    @ratf.protect(
        required_scope="orders:write",
        transactional=True,
        policy=checkout_policy,
    )
    def create_order():
        payload = request.get_json(silent=True) or {}
        product = str(payload.get("product", "Kopi Nusantara"))
        quantity = max(1, min(int(payload.get("quantity", 1)), 10))
        unit_price = max(0, int(payload.get("unit_price", 89000)))
        return (
            jsonify(
                {
                    "status": "order_created",
                    "order_id": f"NUSA-{uuid.uuid4().hex[:8].upper()}",
                    "product": product,
                    "quantity": quantity,
                    "total": quantity * unit_price,
                    "message": "Pesanan diterima oleh backend NusaMart.",
                }
            ),
            201,
        )

    @app.post("/app/api/reset")
    def reset_demo():
        if not _local_request():
            return jsonify({"error": "local_access_only"}), 403
        ratf.engine.reset()
        audit_logger.clear()
        ratf.update_policy(shadow_mode=False)
        return jsonify({"status": "reset", "shadow_mode": False})

    @app.post("/app/api/shadow-mode")
    def shadow_mode():
        if not _local_request():
            return jsonify({"error": "local_access_only"}), 403
        payload = request.get_json(silent=True) or {}
        enabled = bool(payload.get("enabled"))
        ratf.update_policy(shadow_mode=enabled)
        return jsonify({"status": "updated", "shadow_mode": enabled})

    @app.get("/app/api/runtime")
    def runtime():
        if not _local_request():
            return jsonify({"error": "local_access_only"}), 403
        snapshot = ratf.debug_snapshot(DEMO_FAMILY, limit=25)
        redis_active = selected_storage.backend_name == "redis"
        checks: list[dict[str, Any]] = [
            {
                "name": "Paket dapat didistribusikan",
                "ready": True,
                "detail": f"ratf-framework {__version__} dimuat dari instalasi Python.",
            },
            {
                "name": "WSGI server lokal",
                "ready": importlib.util.find_spec("waitress") is not None,
                "detail": "Showcase dijalankan dengan Waitress, bukan Flask development server.",
            },
            {
                "name": "State lintas instance",
                "ready": redis_active,
                "detail": "Redis demo aktif pada database khusus." if redis_active else "Memory storage hanya sesuai untuk demonstrasi satu proses.",
            },
            {
                "name": "Identity Provider produksi",
                "ready": False,
                "detail": "Showcase memakai token lokal; aplikasi nyata harus menghubungkan OAuth/OIDC miliknya.",
            },
            {
                "name": "HTTPS dan secret manager",
                "ready": False,
                "detail": "Belum disediakan oleh proses lokal ini.",
            },
            {
                "name": "High availability dan observability",
                "ready": False,
                "detail": "Redis failover, metrics, tracing, alerting, dan uji multi-node masih diperlukan.",
            },
        ]
        return jsonify(
            {
                "distribution": {
                    "name": "ratf-framework",
                    "version": __version__,
                    "loaded_from": _package_location(),
                },
                "deployment": {
                    "demonstration_ready": True,
                    "integration_ready": True,
                    "production_ready": all(item["ready"] for item in checks),
                    "classification": "alpha — siap demonstrasi dan integrasi terbatas, belum siap produksi skala besar",
                    "checks": checks,
                },
                "state": snapshot,
                "audit_integrity": audit_logger.verify_integrity(),
            }
        )

    @app.get("/account/verification")
    def verification():
        return jsonify(
            {
                "status": "step_up_placeholder",
                "owner": "NusaMart Identity Provider",
                "message": "Pada aplikasi nyata, halaman ini dihubungkan ke OTP, passkey, atau MFA milik pengembang.",
            }
        )

    return app


def run(
    host: str = "127.0.0.1",
    port: int | None = None,
    *,
    open_browser: bool = True,
) -> None:
    from waitress import serve

    selected_port = int(port or os.getenv("RATF_SHOWCASE_PORT", "5100"))
    url = f"http://{host}:{selected_port}/"
    print(f"NusaMart + R-ATF {__version__}: {url}")
    print(f"R-ATF Control Room       : {url}ratf/dashboard/")
    print("Hentikan server dengan tombol Stop di PyCharm/VS Code.")
    if open_browser:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    serve(create_showcase_app(), host=host, port=selected_port, threads=4)


def main() -> None:
    run()


if __name__ == "__main__":
    main()
