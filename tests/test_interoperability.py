from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import threading
import time
import unittest
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from werkzeug.serving import make_server

from examples.flask_app.app import create_app
from tests.common import authzen_payload


class InteroperabilityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.app = create_app(
            audit_path=str(Path(self.temp.name) / "interoperability-audit.jsonl")
        )
        self.app.testing = True
        self.client = self.app.test_client()
        self.app.extensions["ratf"].engine.reset()

    def tearDown(self):
        self.temp.cleanup()

    def test_authzen_contract_and_request_id(self):
        denied = self.client.post("/access/v1/evaluation", json=authzen_payload())
        self.assertEqual(denied.status_code, 401)

        allowed = self.client.post(
            "/access/v1/evaluation",
            json=authzen_payload(),
            headers={"Authorization": "Bearer local-authzen-service-key", "X-Request-ID": "contract-001"},
        )
        self.assertEqual(allowed.status_code, 200)
        self.assertTrue(allowed.get_json()["decision"])
        self.assertEqual(allowed.headers["X-Request-ID"], "contract-001")
        self.assertEqual(allowed.get_json()["context"]["ratf"]["decision"], "allow")
        self.assertEqual(allowed.get_json()["context"]["ratf"]["policy_name"], "default")

        changed = self.client.post(
            "/access/v1/evaluation",
            json=authzen_payload(ip="103.10.20.30", user_agent="AutomationClient/4.0", device_id="other", hour=23),
            headers={"Authorization": "Bearer local-authzen-service-key"},
        )
        self.assertFalse(changed.get_json()["decision"])
        self.assertEqual(changed.get_json()["context"]["ratf"]["decision"], "block")

    @unittest.skipUnless(shutil.which("node"), "Node.js is not installed")
    def test_node_policy_enforcement_point(self):
        server = make_server("127.0.0.1", 5111, self.app)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        node_dir = Path(__file__).resolve().parents[1] / "examples" / "nodejs"
        environment = os.environ.copy()
        environment.update(
            PORT="5222",
            RATF_EVALUATION_URL="http://127.0.0.1:5111/access/v1/evaluation",
            RATF_EVALUATION_KEY="local-authzen-service-key",
        )
        process = subprocess.Popen(
            [shutil.which("node"), "server.mjs"],
            cwd=node_dir,
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        try:
            for _ in range(30):
                try:
                    urlopen("http://127.0.0.1:5222/", timeout=0.2)
                except HTTPError:
                    break
                except URLError:
                    time.sleep(0.1)
            request = Request(
                "http://127.0.0.1:5222/orders",
                data=b'{"item":"Phone"}',
                headers={
                    "Authorization": "Bearer node-app-token",
                    "Content-Type": "application/json",
                    "X-Client-IP": "192.168.10.10",
                    "User-Agent": "MarketplaceNode/1.0",
                    "X-Hour-UTC": "10",
                },
                method="POST",
            )
            with urlopen(request, timeout=5) as response:
                body = json.loads(response.read())
                self.assertEqual(response.status, 201)
                self.assertEqual(body["ratf"]["decision"], "allow")
                self.assertEqual(body["ratf"]["policy_name"], "important-api")
        finally:
            process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=3)
            if process.stdout:
                process.stdout.close()
            if process.stderr:
                process.stderr.close()
            server.shutdown()
            thread.join(timeout=3)
