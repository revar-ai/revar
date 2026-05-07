#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Bump the version in every place that mentions it.

We ship `resurf` and `resurf-models` in lockstep at the same version, with
`resurf`'s pyproject pinned to `resurf-models==<same>`. This script keeps the
four call-sites in sync:

    packages/core-py/pyproject.toml          project.version
    packages/core-py/pyproject.toml          dependencies (resurf-models pin)
    packages/core-py/resurf/__init__.py       __version__
    packages/shared-models/pyproject.toml    project.version

Usage:
    scripts/bump_version.py 0.1.1
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

CORE_PYPROJECT = REPO / "packages" / "core-py" / "pyproject.toml"
CORE_INIT = REPO / "packages" / "core-py" / "resurf" / "__init__.py"
MODELS_PYPROJECT = REPO / "packages" / "shared-models" / "pyproject.toml"

VERSION_RE = re.compile(r"^\d+\.\d+\.\d+(?:[a-zA-Z0-9.\-+]*)?$")


def replace_one(path: Path, pattern: str, replacement: str) -> None:
    """Apply a single regex substitution; require exactly one match."""
    text = path.read_text()
    new_text, n = re.subn(pattern, replacement, text, count=1, flags=re.MULTILINE)
    if n != 1:
        raise SystemExit(
            f"Refusing to write {path}: pattern matched {n} times (expected 1).\n"
            f"  pattern: {pattern!r}"
        )
    path.write_text(new_text)
    print(f"  updated {path.relative_to(REPO)}")


def main(argv: list[str]) -> int:
    if len(argv) != 2 or not VERSION_RE.match(argv[1]):
        print(__doc__, file=sys.stderr)
        return 2
    version = argv[1]
    print(f"Bumping all version sites to {version}")

    replace_one(
        CORE_PYPROJECT,
        r'^version\s*=\s*"[^"]+"',
        f'version = "{version}"',
    )
    replace_one(
        CORE_PYPROJECT,
        r'"resurf-models==[^"]+"',
        f'"resurf-models=={version}"',
    )
    replace_one(
        CORE_INIT,
        r'^__version__\s*=\s*"[^"]+"',
        f'__version__ = "{version}"',
    )
    replace_one(
        MODELS_PYPROJECT,
        r'^version\s*=\s*"[^"]+"',
        f'version = "{version}"',
    )
    print("Done. Review with `git diff`, commit, then tag with:")
    print(f"  git tag v{version} && git push --tags")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
