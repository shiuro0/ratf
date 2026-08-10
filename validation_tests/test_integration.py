from __future__ import annotations

import unittest
import uuid

from examples.flask_app.app import create_app
from validation_tests.common import request_headers


class FlaskExtensionIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.testing = True
        self.client = self.app.test_client()
        self.app.extensions["ratf"].engine.reset()

    def test_allow_replay_and_step_up_flow(self):
        normal = self.client.post("/api/orders", json={"item": "Phone"}, headers=request_headers())
        self.assertEqual(normal.status_code, 201)
        self.assertEqual(normal.headers["X-RATF-Decision"], "allow")

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
