from __future__ import annotations

import unittest
import uuid

from examples.flask_app.app import create_app
from validation_tests.common import authzen_payload, request_headers


class SecurityTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.testing = True
        self.client = self.app.test_client()
        self.extension = self.app.extensions["ratf"]
        self.extension.engine.reset()

    def test_missing_and_invalid_tokens_are_blocked(self):
        missing = self.client.post("/api/orders", json={})
        invalid = self.client.post(
            "/api/orders",
            json={},
            headers=request_headers(token="forged-token"),
        )
        self.assertEqual(missing.status_code, 401)
        self.assertEqual(missing.get_json()["reason_code"], "missing_bearer_token")
        self.assertEqual(invalid.status_code, 401)
        self.assertEqual(invalid.get_json()["reason_code"], "invalid_token")

    def test_shadow_mode_does_not_bypass_authentication_or_replay(self):
        self.extension.update_policy(shadow_mode=True)
        self.assertEqual(self.client.post("/api/orders", json={}).status_code, 401)
        nonce, idem = f"n_{uuid.uuid4().hex}", f"i_{uuid.uuid4().hex}"
        headers = request_headers(nonce=nonce, idempotency_key=idem)
        self.assertEqual(self.client.post("/api/orders", json={}, headers=headers).status_code, 201)
        replay = self.client.post("/api/orders", json={}, headers=headers)
        self.assertEqual(replay.status_code, 409)
        self.assertEqual(replay.get_json()["reason_code"], "nonce_reused")

    def test_scope_is_enforced_by_authzen_service(self):
        payload = authzen_payload(scopes=["catalog:read"])
        response = self.client.post(
            "/access/v1/evaluation",
            json=payload,
            headers={"Authorization": "Bearer local-authzen-service-key"},
        )
        ratf = response.get_json()["context"]["ratf"]
        self.assertFalse(response.get_json()["decision"])
        self.assertEqual(ratf["reason_code"], "insufficient_scope")

        payload["context"]["policy_id"] = "policy-that-does-not-exist"
        unknown = self.client.post(
            "/access/v1/evaluation",
            json=payload,
            headers={"Authorization": "Bearer local-authzen-service-key"},
        )
        self.assertEqual(unknown.status_code, 400)
        self.assertEqual(unknown.get_json()["error"], "unknown_policy")

    def test_audit_hash_chain_remains_valid(self):
        self.client.post("/api/orders", json={}, headers=request_headers())
        report = self.extension.audit_logger.verify_integrity()
        self.assertTrue(report["valid"], report["errors"])
        self.assertGreater(report["entries"], 0)
