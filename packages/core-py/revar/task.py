# SPDX-License-Identifier: Apache-2.0
"""Task definition, schema validation, parameterized generation, and success evaluation."""

from __future__ import annotations

import importlib
import json
import re
from collections.abc import Iterable
from dataclasses import asdict, dataclass, field
from itertools import product
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator

_SCHEMA_PATH = Path(__file__).parent / "schemas" / "task.schema.json"
_SCHEMA_CACHE: dict | None = None


def _load_schema() -> dict:
    global _SCHEMA_CACHE
    if _SCHEMA_CACHE is None:
        _SCHEMA_CACHE = json.loads(_SCHEMA_PATH.read_text())
    return _SCHEMA_CACHE


@dataclass
class Budget:
    max_steps: int = 30
    max_tokens: int = 100_000
    max_wall_clock_s: int = 180


@dataclass
class EvalResult:
    passed: bool
    reason: str
    detail: dict[str, Any] = field(default_factory=dict)


@dataclass
class Task:
    id: str
    site: str
    category: str
    goal: str
    success: dict[str, Any]
    seed: int = 42
    hardness: str = "medium"
    viewport: str = "desktop"
    parameters: dict[str, Any] = field(default_factory=dict)
    modifiers: dict[str, Any] = field(default_factory=dict)
    budget: Budget = field(default_factory=Budget)
    user_credentials: dict[str, str] | None = None
    tags: list[str] = field(default_factory=list)
    description: str | None = None
    source_path: Path | None = None

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    @classmethod
    def from_yaml(cls, path: str | Path) -> Task:
        p = Path(path)
        data = yaml.safe_load(p.read_text())
        validate_task_dict(data)
        return cls.from_dict(data, source_path=p)

    @classmethod
    def from_dict(cls, data: dict[str, Any], *, source_path: Path | None = None) -> Task:
        budget_data = data.get("budget") or {}
        return cls(
            id=data["id"],
            site=data["site"],
            category=data["category"],
            goal=data["goal"],
            success=data["success"],
            seed=int(data.get("seed", 42)),
            hardness=data.get("hardness", "medium"),
            viewport=data.get("viewport", "desktop"),
            parameters=data.get("parameters") or {},
            modifiers=data.get("modifiers") or {},
            budget=Budget(**budget_data),
            user_credentials=data.get("user_credentials"),
            tags=data.get("tags") or [],
            description=data.get("description"),
            source_path=source_path,
        )

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d.pop("source_path", None)
        return d

    # ------------------------------------------------------------------
    # Evaluation
    # ------------------------------------------------------------------

    def evaluate(self, env: Environment) -> EvalResult:  # noqa: F821
        success_type = self.success.get("type")
        if success_type == "state_predicate":
            return self._eval_state_predicate(env)
        if success_type == "python":
            return self._eval_python(env)
        return EvalResult(False, f"unknown_success_type:{success_type}")

    def _eval_state_predicate(self, env) -> EvalResult:
        from .runtime import substitute_bindings

        sql = self.success["query"]
        predicate = self.success["predicate"]
        also = self.success.get("also_assert", []) or []

        bindings = env.default_bindings()
        rendered_sql = substitute_bindings(sql, bindings)
        rows = env.query(rendered_sql)
        result = rows[0]["count"] if (rows and "count" in rows[0]) else (
            next(iter(rows[0].values())) if rows else None
        )

        try:
            primary = bool(eval(predicate, {"__builtins__": {}}, {"result": result, "rows": rows}))
        except Exception as exc:
            return EvalResult(False, f"predicate_error:{exc}", {"sql": rendered_sql})

        details: dict[str, Any] = {"primary_query": rendered_sql, "primary_rows": rows}
        if not primary:
            return EvalResult(False, "primary_predicate_false", details)

        for clause in also:
            ok, reason = _evaluate_assertion(clause, env)
            details.setdefault("also", []).append({"clause": clause, "ok": ok, "reason": reason})
            if not ok:
                return EvalResult(False, f"also_assert_failed:{clause}", details)

        return EvalResult(True, "ok", details)

    def _eval_python(self, env) -> EvalResult:
        module = importlib.import_module(self.success["module"])
        fn = getattr(module, self.success["function"])
        result = fn(env)
        if isinstance(result, EvalResult):
            return result
        if isinstance(result, bool):
            return EvalResult(result, "python_predicate", {})
        if isinstance(result, tuple) and len(result) == 2:
            ok, reason = result
            return EvalResult(bool(ok), str(reason), {})
        return EvalResult(False, f"unexpected_python_return:{type(result).__name__}", {})


_ASSERT_PATTERN = re.compile(r"^(?P<sql>.+?)\s+(?P<op>==|!=|>=|<=|>|<)\s+(?P<rhs>-?\d+)\s*$", re.S)


def _evaluate_assertion(clause: str, env) -> tuple[bool, str]:
    """Evaluate a `<sql> <op> <int>` style also_assert clause."""
    from .runtime import substitute_bindings

    m = _ASSERT_PATTERN.match(clause.strip())
    if not m:
        return False, f"unparseable_clause:{clause}"
    sql = substitute_bindings(m.group("sql").strip(), env.default_bindings())
    rhs = int(m.group("rhs"))
    rows = env.query(sql)
    if not rows:
        return False, "no_rows"
    val = next(iter(rows[0].values()))
    op = m.group("op")
    cmp = {
        "==": lambda a, b: a == b,
        "!=": lambda a, b: a != b,
        ">": lambda a, b: a > b,
        "<": lambda a, b: a < b,
        ">=": lambda a, b: a >= b,
        "<=": lambda a, b: a <= b,
    }[op]
    return bool(cmp(val, rhs)), f"got={val} {op} {rhs}"


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def validate_task_dict(data: dict[str, Any]) -> None:
    validator = Draft202012Validator(_load_schema())
    errors = sorted(validator.iter_errors(data), key=lambda e: e.path)
    if errors:
        msgs = []
        for e in errors:
            path = "/".join(str(p) for p in e.absolute_path) or "<root>"
            msgs.append(f"  {path}: {e.message}")
        raise ValueError("Task does not match schema:\n" + "\n".join(msgs))


# ---------------------------------------------------------------------------
# TaskGenerator (parameterized batch generation)
# ---------------------------------------------------------------------------


@dataclass
class TaskGenerator:
    """Generate a list of Task objects by sweeping parameter combinations.

    Example:
        gen = TaskGenerator(
            template_path="templates/checkout/buy_x_with_coupon.yaml.j2",
            site="shop_v1",
            parameters={
                "qty": [1, 2, 3],
                "product": ["acme-bluetooth-speaker", "trailmate-water-bottle"],
                "coupon": ["SUMMER15", "WELCOME10"],
            },
        )
        for task in gen.generate():
            ...
    """

    template_path: str
    site: str
    parameters: dict[str, list[Any]]
    base_overrides: dict[str, Any] = field(default_factory=dict)

    def generate(self) -> Iterable[Task]:
        from .templating import render_template_to_dict

        keys = list(self.parameters.keys())
        for combo in product(*[self.parameters[k] for k in keys]):
            ctx = {k: v for k, v in zip(keys, combo, strict=False)}
            data = render_template_to_dict(self.template_path, ctx)
            data.update(self.base_overrides)
            validate_task_dict(data)
            yield Task.from_dict(data)
