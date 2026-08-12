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


DEMO_TOKEN = "uhamka-mart-demo-access-token-full-value"
DEMO_FAMILY = "uhamka-mart-customer-family"
DEMO_EXPERIMENT_KEY = "uhamka-mart-local-context-key-32-bytes"
DEMO_POLICY_NAME = "uhamka-mart-checkout"


def _package_location() -> str:
    try:
        return str(Path(distribution("ratf").locate_file("")).resolve())
    except PackageNotFoundError:
        return str(Path(__file__).resolve().parents[2])


def _identity_provider(access_token, _context):
    if access_token != DEMO_TOKEN:
        return None
    return {
        "active": True,
        "subject": "customer-uhamka-001",
        "client_id": "uhamka-mart-web",
        "scope": "catalog:read orders:write",
        "token_id": "uhamka-mart-demo-token-id",
        "family_id": DEMO_FAMILY,
        "metadata": {
            "sub": "customer-uhamka-001",
            "client_id": "uhamka-mart-web",
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
            "owner": "Penyedia Identitas UHAMKA Mart",
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
        token_hash_secret="uhamka-mart-local-token-hash-secret",
        audit_log_secret="uhamka-mart-local-audit-chain-secret",
    )
    selected_storage = storage or create_storage(settings)
    core_config = CoreConfig.from_settings(settings)
    core_config.device_proof_required = False

    app = Flask(__name__)
    app.config.update(
        RATF_CORE_CONFIG=core_config,
        RATF_DASHBOARD_ENABLED=True,
        RATF_DASHBOARD_UNSAFE_LOCAL=True,
        RATF_DASHBOARD_DEFAULT_POLICY=DEMO_POLICY_NAME,
        RATF_DASHBOARD_DEMO_CONTEXT={
            "application_name": "UHAMKA Mart",
            "endpoint": "/api/store/orders",
            "reset_endpoint": "/app/api/reset",
            "shadow_endpoint": "/app/api/shadow-mode",
            "access_token": DEMO_TOKEN,
            "authorization_header": f"Bearer {DEMO_TOKEN}",
            "client_id": "uhamka-mart-web",
            "device_id": "browser-customer-001",
            "normal_ip": "192.168.10.10",
            "normal_hour": 10,
            "experiment_key": DEMO_EXPERIMENT_KEY,
            "policy_name": DEMO_POLICY_NAME,
            "warning": "Token ini hanya data demonstrasi lokal dan sengaja ditampilkan lengkap.",
        },
        RATF_AUTHZEN_ENABLED=True,
        RATF_AUTHZEN_API_KEY="uhamka-mart-local-authzen-key",
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
    ratf.policy(
        DEMO_POLICY_NAME,
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
        return render_template("ratf/showcase.html")

    @app.get("/app/api/bootstrap")
    def bootstrap():
        return jsonify(
            {
                "application": {
                    "name": "UHAMKA Mart",
                    "owner": "Aplikasi contoh milik pengembang pengguna R-ATF",
                    "endpoint": "/api/store/orders",
                },
                "module": {
                    "distribution": "ratf",
                    "version": __version__,
                    "loaded_from": _package_location(),
                    "policy": ratf.policy_config(DEMO_POLICY_NAME),
                    "storage": selected_storage.backend_name,
                },
                "client": {
                    "access_token": DEMO_TOKEN,
                    "client_id": "uhamka-mart-web",
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
        policy=DEMO_POLICY_NAME,
    )
    def create_order():
        payload = request.get_json(silent=True) or {}
        raw_items = payload.get("items")
        if not isinstance(raw_items, list) or not raw_items:
            raw_items = [
                {
                    "product": payload.get("product", "Produk UHAMKA Mart"),
                    "quantity": payload.get("quantity", 1),
                    "unit_price": payload.get("unit_price", 89000),
                }
            ]
        items = []
        for raw in raw_items[:12]:
            if not isinstance(raw, dict):
                continue
            quantity = max(1, min(int(raw.get("quantity", 1)), 10))
            unit_price = max(0, int(raw.get("unit_price", 0)))
            items.append(
                {
                    "product": str(raw.get("product", "Produk UHAMKA Mart")),
                    "quantity": quantity,
                    "unit_price": unit_price,
                    "subtotal": quantity * unit_price,
                }
            )
        if not items:
            return jsonify({"error": "items_required"}), 400
        subtotal = sum(item["subtotal"] for item in items)
        discount = max(0, min(int(payload.get("discount", 0)), subtotal))
        shipping_cost = max(0, int(payload.get("shipping_cost", 0)))
        return (
            jsonify(
                {
                    "status": "order_created",
                    "order_id": f"UHM-{uuid.uuid4().hex[:8].upper()}",
                    "items": items,
                    "item_count": sum(item["quantity"] for item in items),
                    "shipping_method": str(
                        payload.get("shipping_method", "regular")
                    ),
                    "subtotal": subtotal,
                    "discount": discount,
                    "shipping_cost": shipping_cost,
                    "total": subtotal - discount + shipping_cost,
                    "message": "Pesanan UHAMKA Mart berhasil dibuat.",
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
        policy = ratf.policy_config(DEMO_POLICY_NAME)["resolved"]
        return jsonify({"status": "reset", "shadow_mode": policy["shadow_mode"]})

    @app.post("/app/api/shadow-mode")
    def shadow_mode():
        if not _local_request():
            return jsonify({"error": "local_access_only"}), 403
        payload = request.get_json(silent=True) or {}
        enabled = bool(payload.get("enabled"))
        ratf.update_policy_profile(DEMO_POLICY_NAME, shadow_mode=enabled)
        return jsonify({"status": "updated", "shadow_mode": enabled})

    @app.get("/app/api/runtime")
    def runtime():
        if not _local_request():
            return jsonify({"error": "local_access_only"}), 403
        snapshot = ratf.debug_snapshot(DEMO_FAMILY, limit=25)
        redis_active = selected_storage.backend_name == "redis"
        checks: list[dict[str, Any]] = [
            {
                "name": "Modul Python dapat dipasang",
                "ready": True,
                "detail": f"ratf {__version__} berhasil dimuat dari instalasi Python.",
            },
            {
                "name": "Server demonstrasi",
                "ready": importlib.util.find_spec("waitress") is not None,
                "detail": "Aplikasi dijalankan dengan Waitress, bukan server pengembangan Flask.",
            },
            {
                "name": "Penyimpanan bersama",
                "ready": redis_active,
                "detail": "Redis aktif pada database demonstrasi khusus." if redis_active else "Penyimpanan memori hanya sesuai untuk demonstrasi satu proses.",
            },
            {
                "name": "Sistem login aplikasi asli",
                "ready": False,
                "detail": "Demo memakai token lokal; aplikasi nyata harus dihubungkan ke sistem login milik pengembang.",
            },
            {
                "name": "Koneksi aman dan pengelolaan kunci",
                "ready": False,
                "detail": "HTTPS dan penyimpanan kunci aman belum disediakan oleh proses lokal ini.",
            },
            {
                "name": "Cadangan dan pemantauan layanan",
                "ready": False,
                "detail": "Pengalihan saat gagal, metrik, penelusuran, peringatan, dan uji beberapa server masih diperlukan.",
            },
        ]
        return jsonify(
            {
                "distribution": {
                    "name": "ratf",
                    "version": __version__,
                    "loaded_from": _package_location(),
                },
                "deployment": {
                    "demonstration_ready": True,
                    "integration_ready": True,
                    "production_ready": all(item["ready"] for item in checks),
                    "classification": "siap untuk demonstrasi dan integrasi awal, belum siap untuk operasi skala besar",
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
                "owner": "Penyedia Identitas UHAMKA Mart",
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
    print(f"UHAMKA Mart + R-ATF {__version__}: {url}")
    print(f"R-ATF Control Room       : {url}ratf/dashboard/")
    print("Hentikan server dengan tombol Stop di PyCharm/VS Code.")
    if open_browser:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    serve(create_showcase_app(), host=host, port=selected_port, threads=4)


def main() -> None:
    run()


if __name__ == "__main__":
    main()
