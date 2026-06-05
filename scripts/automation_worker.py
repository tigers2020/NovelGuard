#!/usr/bin/env python3
"""Run one automation job. For continuous Linear automation use automation_daemon.py.

Usage:
  python scripts/automation_daemon.py          # webhook + worker (recommended)
  python scripts/automation_worker.py --once   # single job only
"""

import runpy
import sys
from pathlib import Path

if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root))
    runpy.run_module("automation.runners.job_worker", run_name="__main__")
