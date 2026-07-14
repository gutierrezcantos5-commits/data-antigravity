# -*- coding: utf-8 -*-
"""
Ejecuta evals Valle/Sax.

Uso:
  python scripts/run_evals.py           # solo CI (como GitHub)
  python scripts/run_evals.py --full    # CI + local (entregables en disco)
  python scripts/run_evals.py --local   # solo evals local
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def main() -> int:
    p = argparse.ArgumentParser(description="Run Antigravity engineering evals")
    p.add_argument("--full", action="store_true", help="CI + local evals")
    p.add_argument("--local", action="store_true", help="Solo evals local")
    p.add_argument("-v", "--verbose", action="store_true")
    args = p.parse_args()

    if args.local:
        marker = "local"
    elif args.full:
        marker = ""
    else:
        marker = "ci"

    cmd = [sys.executable, "-m", "pytest", "tests/evals", "-v" if args.verbose else "-q"]
    if marker:
        cmd.extend(["-m", marker])

    print(" ".join(cmd))
    return subprocess.call(cmd, cwd=REPO_ROOT)


if __name__ == "__main__":
    raise SystemExit(main())
