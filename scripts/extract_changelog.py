#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Print the CHANGELOG.md section for a given version on stdout.

The release workflow pipes this output into the GitHub Release notes.
Falls back to a placeholder if the section is missing so a release isn't
blocked by a docs gap.

Usage:
    scripts/extract_changelog.py 0.1.1
"""

from __future__ import annotations

import sys
from pathlib import Path

CHANGELOG = Path(__file__).resolve().parent.parent / "CHANGELOG.md"


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    version = argv[1]
    if not CHANGELOG.exists():
        print(f"No CHANGELOG.md found; release notes for v{version} will be empty.")
        return 0

    lines = CHANGELOG.read_text().splitlines()
    start: int | None = None
    end: int | None = None
    target = f"## [{version}]"
    for i, line in enumerate(lines):
        if line.startswith(target):
            start = i + 1
            continue
        if start is not None and line.startswith("## ["):
            end = i
            break

    if start is None:
        print(f"_(No changelog entry found for v{version}.)_")
        return 0
    chunk = "\n".join(lines[start:end]).strip()
    print(chunk if chunk else f"_(Empty changelog entry for v{version}.)_")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
