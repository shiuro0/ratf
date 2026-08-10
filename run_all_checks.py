from __future__ import annotations

import json
import sys
import time
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
for path in (ROOT / "src", ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from validation_tests.test_performance import run_core_benchmark
from ratf import __version__

CATEGORIES = {
    "regression": "validation_tests.test_regression",
    "integration": "validation_tests.test_integration",
    "interoperability": "validation_tests.test_interoperability",
    "security": "validation_tests.test_security",
    "performance": "validation_tests.test_performance",
}


def main() -> int:
    summary = {
        "framework_version": __version__,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "categories": {},
    }
    all_ok = True
    for category, module in CATEGORIES.items():
        print(f"\n{'=' * 64}\n{category.upper()} TEST\n{'=' * 64}")
        suite = unittest.defaultTestLoader.loadTestsFromName(module)
        started = time.perf_counter()
        result = unittest.TextTestRunner(verbosity=2).run(suite)
        category_result = {
            "tests_run": result.testsRun,
            "passed": result.testsRun - len(result.failures) - len(result.errors) - len(result.skipped),
            "failures": len(result.failures),
            "errors": len(result.errors),
            "skipped": len(result.skipped),
            "duration_seconds": round(time.perf_counter() - started, 4),
            "status": "PASS" if result.wasSuccessful() else "FAIL",
        }
        summary["categories"][category] = category_result
        all_ok = all_ok and result.wasSuccessful()

    print("\nMenjalankan microbenchmark core 5.000 evaluasi...")
    summary["performance_metrics"] = run_core_benchmark(5000)
    summary["overall_status"] = "PASS" if all_ok else "FAIL"
    output_dir = ROOT / "results" / "v0_1_validation"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "validation_summary.json"
    output_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    print("\nRingkasan:")
    for category, result in summary["categories"].items():
        print(f"- {category:18} {result['status']} ({result['passed']}/{result['tests_run']} lulus)")
    print("- performance metrics", summary["performance_metrics"])
    print("- hasil tersimpan di", output_path)
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
