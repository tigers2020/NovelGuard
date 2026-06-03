#!/usr/bin/env python3
"""Enqueue automation job. Usage: python scripts/automation_enqueue.py --kind implement --task '...'"""

import runpy
import sys
from pathlib import Path

if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root))
    runpy.run_module("automation.runners.enqueue_job", run_name="__main__")
