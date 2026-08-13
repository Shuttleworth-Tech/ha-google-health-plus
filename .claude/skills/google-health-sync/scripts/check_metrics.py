#!/usr/bin/env python3
"""Diff google-health-api data types vs sensors exposed by google_health_plus.

Lists library sub-API accessors that the integration never calls, so new
metrics can be triaged. Deterministic — needs no Google credentials.

Run from the repo root:
    ./.claude/skills/google-health-sync/scripts/check_metrics.py
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
COMPONENT = REPO / "custom_components" / "google_health_plus"

# Accessors that are infrastructure, not health data.
NON_METRIC = {
    "paired_devices",
    "operations",
    "subscriptions",
    "subscribers",
    "_session",
}


def library_accessors() -> set[str]:
    """Extract data-type accessor names from the library's GoogleHealthApi."""
    script = (
        "import inspect, google_health_api.api as m; "
        "src = inspect.getsource(m.GoogleHealthApi.__init__); "
        "print(src)"
    )
    venv_python = REPO / ".venv" / "bin" / "python"
    interpreter = str(venv_python) if venv_python.exists() else sys.executable
    out = subprocess.run(
        [interpreter, "-c", script], capture_output=True, text=True, check=True
    ).stdout
    return set(re.findall(r"self\.([a-z_]+)\s*=", out))


def called_accessors() -> set[str]:
    """Accessors the integration's coordinators actually call."""
    called = set()
    for py in COMPONENT.glob("*.py"):
        called |= set(re.findall(r"api(?:_client)?\.([a-z_]+)\.", py.read_text()))
    return called


def main() -> int:
    lib = library_accessors() - NON_METRIC
    called = called_accessors() & lib
    unmapped = sorted(lib - called)
    print(f"Library data types: {len(lib)}")
    print(f"Exposed by integration: {len(called)}")
    print(f"\nUnmapped ({len(unmapped)}):")
    for name in unmapped:
        print(f"  - {name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
