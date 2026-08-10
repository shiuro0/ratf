from __future__ import annotations

import tempfile
import unittest
import uuid
from datetime import datetime, timezone
from pathlib import Path

from examples.flask_app.app import create_app
from ratf.showcase import (
    DEMO_EXPERIMENT_KEY,
    DEMO_POLICY_NAME,
    DEMO_TOKEN,
    create_showcase_app,
)
from validation_tests.common import request_headers


class FlaskExtensionIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.app = create_app(
            audit_path=str(Path(self.temp.name) / "integration-audit.jsonl")
        )
        self.app.testing = True
        self.client = self.app.test_client()
        self.app.extensions["ratf"].engine.reset()

    def tearDown(self):
        self.temp.cleanup()

    def test_allow_replay_and_step_up_flow(self):
        normal = self.client.post("/api/orders", json={"item": "Phone"}, headers=request_headers())
        self.assertEqual(normal.status_code, 201)
        self.assertEqual(normal.headers["X-RATF-Decision"], "allow")
        debug = self.app.extensions["ratf"].debug_snapshot("family-customer-001")
        self.assertEqual(debug["storage_backend"], "memory")
        self.assertEqual(debug["context_history"]["allowed_request_count"], 1)
        self.assertGreaterEqual(len(debug["recent_events"]), 1)

        nonce, idem = f"n_{uuid.uuid4().hex}", f"i_{uuid.uuid4().hex}"
        headers = request_headers(nonce=nonce, idempotency_key=idem)
        self.assertEqual(self.client.post("/api/orders", json={}, headers=headers).status_code, 201)
        replay = self.client.post("/api/orders", json={}, headers=headers)
        self.assertEqual(replay.status_code, 409)
        self.assertEqual(replay.get_json()["reason_code"], "nonce_reused")

        changed = self.client.post(
            "/api/orders",
            json={"item": "Phone"},
            headers=request_headers(ip="103.10.20.30", user_agent="PythonBot/3.0", hour=23),
        )
        self.assertEqual(changed.status_code, 401)
        self.assertEqual(changed.get_json()["decision"], "verify")
        self.assertEqual(changed.get_json()["step_up"]["challenge_type"], "reauthentication")

    def test_weights_can_be_changed_without_editing_source(self):
        profiles = self.client.get("/ratf/dashboard/api/policies").get_json()
        self.assertIn("important-api", profiles["profiles"])
        self.assertEqual(
            profiles["profiles"]["important-api"]["resolved"]["allow_threshold"],
            0.88,
        )
        payment = self.client.post(
            "/api/payments",
            json={"amount": 250000},
            headers=request_headers(),
        )
        self.assertEqual(payment.status_code, 201)
        self.assertEqual(payment.headers["X-RATF-Policy"], "important-api")
        preflight = self.client.options("/api/payments")
        self.assertEqual(preflight.status_code, 200)
        self.assertNotIn("X-RATF-Decision", preflight.headers)

        research = self.client.get("/ratf/dashboard/api/research-summary")
        self.assertEqual(research.status_code, 200)
        research_data = research.get_json()
        if research_data.get("available"):
            self.assertEqual(research_data["security_rows"], 31220)
            self.assertEqual(research_data["measured_runs"], 40)
        updated = self.client.put(
            "/ratf/dashboard/api/config",
            json={
                "weights": {"ip": 0, "device": 0, "time": 0, "frequency": 1, "token_history": 0},
                "verify_threshold": 0.62,
                "allow_threshold": 0.82,
                "shadow_mode": False,
            },
        )
        self.assertEqual(updated.status_code, 200)
        evaluated = self.client.post(
            "/ratf/dashboard/api/evaluate",
            json={"request_count": 25, "required_scope": "orders:write", "reset": True},
        )
        self.assertEqual(evaluated.status_code, 200)
        self.assertEqual(evaluated.get_json()["result"]["trust_score"], 0.6)
        self.assertEqual(evaluated.get_json()["result"]["decision"], "block")
        profiled = self.client.post(
            "/ratf/dashboard/api/evaluate",
            json={
                "policy_id": "important-api",
                "request_count": 2,
                "required_scope": "orders:write",
                "reset": True,
            },
        )
        self.assertEqual(profiled.status_code, 200)
        self.assertEqual(profiled.get_json()["result"]["policy_name"], "important-api")
        self.assertEqual(self.app.extensions["ratf"].engine.config.weights()["frequency"], 1.0)
        with self.assertRaises(ValueError):
            self.app.extensions["ratf"].policy(
                "invalid-thresholds",
                thresholds={"verify": 0.90, "allow": 0.80},
            )

    def test_shadow_mode_observes_risk_but_forwards_request(self):
        extension = self.app.extensions["ratf"]
        extension.update_policy(shadow_mode=True)
        self.client.post("/api/orders", json={}, headers=request_headers())
        changed = self.client.post(
            "/api/orders",
            json={},
            headers=request_headers(ip="103.10.20.30", user_agent="PythonBot/3.0", hour=23),
        )
        self.assertEqual(changed.status_code, 201)
        self.assertEqual(changed.headers["X-RATF-Decision"], "verify")
        self.assertEqual(changed.headers["X-RATF-Effective-Decision"], "allow")
        self.assertEqual(changed.headers["X-RATF-Shadow-Mode"], "true")


class InstalledShowcaseIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.app = create_showcase_app(
            audit_path=str(Path(self.temp.name) / "showcase-audit.jsonl")
        )
        self.app.testing = True
        self.client = self.app.test_client()

    def tearDown(self):
        self.temp.cleanup()

    @staticmethod
    def headers(*, ip="192.168.10.10", device="browser-customer-001", hour=10):
        context_time = datetime.now(timezone.utc).replace(
            hour=hour,
            minute=0,
            second=0,
            microsecond=0,
        )
        return {
            "Authorization": f"Bearer {DEMO_TOKEN}",
            "X-Client-Id": "uhamka-mart-web",
            "X-Device-Id": device,
            "X-Request-Timestamp": str(int(context_time.timestamp())),
            "X-Request-Nonce": f"nonce_{uuid.uuid4().hex}",
            "Idempotency-Key": f"idem_{uuid.uuid4().hex}",
            "X-Request-Id": f"request_{uuid.uuid4().hex}",
            "X-Scenario-Label": "showcase_validation",
            "X-Experiment-Key": DEMO_EXPERIMENT_KEY,
            "X-Test-Source-IP": ip,
            "X-Test-Context-Time": context_time.isoformat(),
            "User-Agent": "UHAMKAMartBrowser/1.0",
        }

    def test_storefront_and_runtime_are_packaged_with_framework(self):
        page = self.client.get("/")
        self.assertEqual(page.status_code, 200)
        self.assertIn(b"UHAMKA Mart", page.data)
        self.assertNotIn(b"trust score", page.data.lower())
        self.assertNotIn(b"threshold", page.data.lower())

        dashboard = self.client.get("/ratf/dashboard/")
        self.assertEqual(dashboard.status_code, 200)
        self.assertIn(b"Gunakan nilai penelitian", dashboard.data)

        bootstrap = self.client.get("/app/api/bootstrap").get_json()
        self.assertEqual(bootstrap["framework"]["distribution"], "ratf-framework")
        self.assertEqual(bootstrap["framework"]["policy"]["name"], DEMO_POLICY_NAME)

        demo_context = self.client.get("/ratf/dashboard/api/demo-context")
        self.assertEqual(demo_context.status_code, 200)
        self.assertEqual(demo_context.get_json()["access_token"], DEMO_TOKEN)
        self.assertIn(DEMO_TOKEN, demo_context.get_json()["authorization_header"])

        research = self.client.get("/ratf/dashboard/api/research-summary").get_json()
        self.assertTrue(research["available"])
        self.assertEqual(research["security_rows"], 31220)
        self.assertEqual(research["measured_runs"], 40)

        runtime = self.client.get("/app/api/runtime").get_json()
        self.assertTrue(runtime["deployment"]["demonstration_ready"])
        self.assertTrue(runtime["deployment"]["integration_ready"])
        self.assertFalse(runtime["deployment"]["production_ready"])

    def test_research_policy_preset_can_be_restored_for_store_endpoint(self):
        changed = self.client.put(
            "/ratf/dashboard/api/config",
            json={
                "policy_id": DEMO_POLICY_NAME,
                "weights": {
                    "ip": 0,
                    "device": 0,
                    "time": 0,
                    "frequency": 1,
                    "token_history": 0,
                },
                "verify_threshold": 0.62,
                "allow_threshold": 0.82,
                "shadow_mode": False,
            },
        )
        self.assertEqual(changed.status_code, 200)
        self.assertEqual(changed.get_json()["policy_name"], DEMO_POLICY_NAME)
        self.assertEqual(changed.get_json()["weights"]["frequency"], 1.0)

        restored = self.client.put(
            "/ratf/dashboard/api/config",
            json={
                "policy_id": DEMO_POLICY_NAME,
                "weights": {
                    "ip": 0.25,
                    "device": 0.20,
                    "time": 0.10,
                    "frequency": 0.20,
                    "token_history": 0.25,
                },
                "verify_threshold": 0.62,
                "allow_threshold": 0.82,
                "shadow_mode": False,
            },
        )
        self.assertEqual(restored.status_code, 200)
        self.assertEqual(restored.get_json()["allow_threshold"], 0.82)
        config = self.client.get(
            f"/ratf/dashboard/api/config?policy_id={DEMO_POLICY_NAME}"
        ).get_json()
        self.assertEqual(config["weights"]["ip"], 0.25)

    def test_allow_verify_block_and_replay_are_visible_to_client(self):
        body = {"product": "Kopi Gayo Pilihan", "quantity": 1, "unit_price": 89000}
        normal_headers = self.headers()
        normal = self.client.post("/api/store/orders", json=body, headers=normal_headers)
        self.assertEqual(normal.status_code, 201)
        self.assertEqual(normal.headers["X-RATF-Decision"], "allow")

        changed = self.client.post(
            "/api/store/orders",
            json=body,
            headers=self.headers(ip="103.77.14.90", device="unknown-device-884"),
        )
        self.assertEqual(changed.status_code, 401)
        self.assertEqual(changed.headers["X-RATF-Decision"], "verify")
        self.assertEqual(changed.get_json()["step_up"]["challenge_type"], "one_time_password")

        high_risk = self.client.post(
            "/api/store/orders",
            json=body,
            headers=self.headers(ip="45.12.210.77", device="automation-device-991", hour=23),
        )
        self.assertEqual(high_risk.status_code, 403)
        self.assertEqual(high_risk.headers["X-RATF-Decision"], "block")

        replay = self.client.post("/api/store/orders", json=body, headers=normal_headers)
        self.assertEqual(replay.status_code, 409)
        self.assertEqual(replay.get_json()["reason_code"], "nonce_reused")
