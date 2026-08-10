from __future__ import annotations

import tempfile
import time
import unittest
import uuid
from dataclasses import replace
from pathlib import Path

from app import create_app as create_legacy_app
from ratf.config import Settings
from ratf.context import body_hash_from_payload
from ratf.device_proof import sign_request


class LegacyRegressionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.settings = replace(
            Settings(),
            storage_backend="memory",
            allow_memory_fallback=True,
            strict_startup=False,
            experiment_mode=True,
            experiment_key="local-experiment-key-32-characters-long",
            admin_token="local-admin-token-change-me",
            device_enrollment_key="local-enrollment-key-change-me",
            log_path=str(Path(self.temp.name) / "legacy.jsonl"),
        )
        app = create_legacy_app(self.settings)
        app.testing = True
        self.client = app.test_client()
        registered = self.client.post(
            "/auth/device/register",
            json={"user_id": "customer-001", "client_id": "marketplace-mobile-app", "device_name": "Laptop"},
            headers={"X-Enrollment-Key": self.settings.device_enrollment_key},
        )
        self.assertEqual(registered.status_code, 201)
        self.device = registered.get_json()
        token = self.client.post(
            "/oauth/token",
            json={
                "user_id": "customer-001",
                "client_id": "marketplace-mobile-app",
                "device_id": self.device["device_id"],
                "device_secret": self.device["device_secret"],
                "scope": "orders:write",
            },
            headers={
                "X-Experiment-Key": self.settings.experiment_key,
                "X-Test-Source-IP": "192.168.10.10",
                "User-Agent": "MarketplaceDesktop/1.0",
            },
        )
        self.assertEqual(token.status_code, 200)
        self.token = token.get_json()["access_token"]
        self.body = {
            "customer_id": "customer-001",
            "items": [{"sku": "SKU-SMARTPHONE-001", "quantity": 1}],
            "shipping_method": "express",
        }

    def tearDown(self):
        self.temp.cleanup()

    def headers(self, nonce: str, idem: str):
        timestamp = str(int(time.time()))
        signature = sign_request(
            self.device["device_secret"],
            "POST",
            "/api/v1/orders",
            body_hash_from_payload(self.body),
            timestamp,
            nonce,
            idem,
        )
        return {
            "Authorization": f"Bearer {self.token}",
            "X-Client-Id": "marketplace-mobile-app",
            "X-Device-Id": self.device["device_id"],
            "X-Request-Timestamp": timestamp,
            "X-Request-Nonce": nonce,
            "Idempotency-Key": idem,
            "X-Device-Signature": signature,
            "X-Experiment-Key": self.settings.experiment_key,
            "X-Test-Source-IP": "192.168.10.10",
            "User-Agent": "MarketplaceDesktop/1.0",
        }

    def test_legacy_normal_request_remains_allowed(self):
        response = self.client.post(
            "/api/v1/orders",
            json=self.body,
            headers=self.headers(f"n_{uuid.uuid4().hex}", f"i_{uuid.uuid4().hex}"),
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.headers["X-RATF-Decision"], "allow")
        self.assertEqual(float(response.headers["X-RATF-Score"]), 1.0)

    def test_legacy_exact_replay_remains_blocked(self):
        headers = self.headers(f"n_{uuid.uuid4().hex}", f"i_{uuid.uuid4().hex}")
        first = self.client.post("/api/v1/orders", json=self.body, headers=headers)
        replay = self.client.post("/api/v1/orders", json=self.body, headers=headers)
        self.assertEqual(first.status_code, 201)
        self.assertEqual(replay.status_code, 409)
        self.assertEqual(replay.get_json()["reason_code"], "nonce_reused")
