# SPDX-License-Identifier: Apache-2.0
"""Small runtime helpers shared across modules."""

from __future__ import annotations

import re
from typing import Any


_BINDING_RE = re.compile(r":([a-zA-Z_][a-zA-Z0-9_]*)")


def substitute_bindings(sql: str, bindings: dict[str, Any]) -> str:
    """Replace :name placeholders in SQL with literal values from bindings.

    We do a best-effort substitution because the SDK's query endpoint accepts
    SQLite-bound parameters, but YAML success.query strings are easier to read
    with values inline. Strings are quoted and single-quote escaped.
    """

    def repl(match: re.Match) -> str:
        key = match.group(1)
        if key not in bindings:
            return match.group(0)
        v = bindings[key]
        if v is None:
            return "NULL"
        if isinstance(v, bool):
            return "1" if v else "0"
        if isinstance(v, (int, float)):
            return str(v)
        return "'" + str(v).replace("'", "''") + "'"

    return _BINDING_RE.sub(repl, sql)
