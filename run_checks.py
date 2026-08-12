from __future__ import annotations

import sys
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
for path in (ROOT / "src", ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from tests.test_performance import run_core_benchmark
from ratf import __version__

CATEGORIES = {
    "regression": "tests.test_regression",
    "integration": "tests.test_integration",
    "interoperability": "tests.test_interoperability",
    "security": "tests.test_security",
    "performance": "tests.test_performance",
}


def main() -> int:
    summary: dict[str, dict[str, int | float | str]] = {}
    all_ok = True
    print(f"R-ATF {__version__} — pemeriksaan repository")
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
        summary[category] = category_result
        all_ok = all_ok and result.wasSuccessful()

    print("\nMenjalankan microbenchmark core 5.000 evaluasi...")
    performance = run_core_benchmark(5000)

    print("\nRingkasan:")
    for category, result in summary.items():
        print(f"- {category:18} {result['status']} ({result['passed']}/{result['tests_run']} lulus)")
    print("- performance metrics", performance)
    print("- status keseluruhan  ", "PASS" if all_ok else "FAIL")
    print("\nTidak ada laporan hasil yang ditulis ke repository.")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
