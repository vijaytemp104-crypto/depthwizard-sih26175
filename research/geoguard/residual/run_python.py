#!/usr/bin/env python3
"""Run research code with the repository's existing offline Python packages."""

from __future__ import annotations

import runpy
import sys
from pathlib import Path


REPOSITORY = Path(__file__).resolve().parents[3]
SITE_PACKAGES = REPOSITORY / ".venv312" / "Lib" / "site-packages"


def main() -> int:
    if not SITE_PACKAGES.is_dir():
        raise SystemExit(f"Existing offline site-packages not found: {SITE_PACKAGES}")
    sys.path.insert(0, str(SITE_PACKAGES))
    sys.path.insert(1, str(REPOSITORY))
    if len(sys.argv) < 2:
        raise SystemExit("usage: run_python.py [-m module | script.py] [args ...]")
    if sys.argv[1] == "-m":
        if len(sys.argv) < 3:
            raise SystemExit("-m requires a module name")
        module = sys.argv[2]
        sys.argv = sys.argv[2:]
        runpy.run_module(module, run_name="__main__", alter_sys=True)
    else:
        script = sys.argv[1]
        sys.argv = sys.argv[1:]
        sys.path.insert(0, str(Path(script).resolve().parent))
        runpy.run_path(script, run_name="__main__")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
