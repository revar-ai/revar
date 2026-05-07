#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Fail if the four version call-sites disagree.

Run from CI (release/preflight job) to refuse to publish a half-bumped repo.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

CORE_PYPROJECT = REPO / "packages" / "core-py" / "pyproject.toml"
CORE_INIT = REPO / "packages" / "core-py" / "resurf" / "__init__.py"
MODELS_PYPROJECT = REPO / "packages" / "shared-models" / "pyproject.toml"


def grep(path: Path, pattern: str, group: int = 1) -> str:
    m = re.search(pattern, path.read_text(), flags=re.MULTILINE)
    if not m:
        raise SystemExit(f"Could not find {pattern!r} in {path}")
    return m.group(group)


def main() -> int:
    versions = {
        "resurf (pyproject)": grep(CORE_PYPROJECT, r'^version\s*=\s*"([^"]+)"'),
        "resurf (__init__)": grep(CORE_INIT, r'^__version__\s*=\s*"([^"]+)"'),
        "resurf-models pin": grep(CORE_PYPROJECT, r'"resurf-models==([^"]+)"'),
        "resurf-models (pyproject)": grep(MODELS_PYPROJECT, r'^version\s*=\s*"([^"]+)"'),
    }
    distinct = set(versions.values())
    if len(distinct) == 1:
        print(f"All version sites agree: {distinct.pop()}")
        return 0

    print("Version sites disagree:")
    for k, v in versions.items():
        print(f"  {k:<28} {v}")
    print("\nRun `scripts/bump_version.py X.Y.Z` to align them.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
