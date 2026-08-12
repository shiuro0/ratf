from __future__ import annotations

import statistics
import time
import unittest
import uuid
from datetime import datetime, timezone

from ratf.core import CoreConfig, EvaluationRequest, Identity, RATFEngine, RequestContext
from ratf.storage import MemoryStorage


def run_core_benchmark(iterations: int = 5000) -> dict:
    config = CoreConfig(device_proof_required=False, nonce_required=False, idempotency_required=False)
    storage = MemoryStorage()
    engine = RATFEngine(config, storage)
    identity = Identity(
        subject="benchmark-user",
        client_id="benchmark-client",
        scopes=("orders:write",),
        family_id="benchmark-family",
        metadata={"issued_ip": "192.168.10.10", "issued_user_agent": "Benchmark/1.0", "issued_hour_utc": 10},
    )
    durations = []
    started_all = time.perf_counter()
    for index in range(iterations):
        now = datetime.now(timezone.utc)
        context = RequestContext(
            request_id=f"bench_{index}_{uuid.uuid4().hex[:6]}",
            run_id="core_benchmark",
            scenario_label="normal",
            source_ip="192.168.10.10",
            user_agent="Benchmark/1.0",
            client_id="benchmark-client",
            device_id="benchmark-device",
            method="POST",
            endpoint="/orders",
            timestamp=now.isoformat(),
            request_timestamp=None,
            hour_utc=10,
            body_hash="0" * 64,
            request_fingerprint=f"fingerprint_{index}",
            nonce=None,
            idempotency_key=None,
            device_signature=None,
        )
        started = time.perf_counter_ns()
        result = engine.evaluate_identity(
            identity,
            EvaluationRequest(context, "orders:write", enforce_request_integrity=False, request_count=1),
        )
        durations.append((time.perf_counter_ns() - started) / 1_000_000)
        if result.decision != "allow":
            raise AssertionError(f"Unexpected benchmark decision: {result.decision}")
    elapsed = time.perf_counter() - started_all
    ordered = sorted(durations)
    p95_index = max(0, min(len(ordered) - 1, int(len(ordered) * 0.95) - 1))
    return {
        "kind": "core_development_microbenchmark",
        "iterations": iterations,
        "mean_ms": round(statistics.fmean(durations), 6),
        "p95_ms": round(ordered[p95_index], 6),
        "stddev_ms": round(statistics.pstdev(durations), 6),
        "throughput_evaluations_per_second": round(iterations / elapsed, 2),
        "elapsed_seconds": round(elapsed, 6),
        "environment_note": "Microbenchmark proses lokal; bukan hasil Docker/Gunicorn/k6 untuk BAB IV.",
    }


class PerformanceSmokeTests(unittest.TestCase):
    def test_core_benchmark_completes(self):
        result = run_core_benchmark(500)
        self.assertEqual(result["iterations"], 500)
        self.assertGreater(result["throughput_evaluations_per_second"], 0)
        self.assertGreaterEqual(result["p95_ms"], 0)
