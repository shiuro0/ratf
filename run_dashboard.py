"""PyCharm entry point for the installed-package showcase."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from ratf.showcase import run


if __name__ == "__main__":
    run()
