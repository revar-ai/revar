# SPDX-License-Identifier: Apache-2.0
"""Jinja2 template rendering for failure-mode templates."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml
from jinja2 import Environment, FileSystemLoader, StrictUndefined


def _slug(value: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "_", value).strip("_").lower()
    return s or "task"


def _slug_filter(value: Any) -> str:
    if isinstance(value, dict):
        for k in ("slug", "name", "id"):
            if k in value:
                return _slug(str(value[k]))
        return "task"
    return _slug(str(value))


def _make_env(template_path: str | Path) -> tuple[Environment, str]:
    p = Path(template_path)
    env = Environment(
        loader=FileSystemLoader(str(p.parent)),
        autoescape=False,
        undefined=StrictUndefined,
        keep_trailing_newline=True,
    )
    env.filters["slug"] = _slug_filter
    return env, p.name


def render_template_text(template_path: str | Path, context: dict[str, Any]) -> str:
    env, name = _make_env(template_path)
    template = env.get_template(name)
    return template.render(**context, slug=_slug_filter)


def render_template_to_dict(template_path: str | Path, context: dict[str, Any]) -> dict[str, Any]:
    text = render_template_text(template_path, context)
    return yaml.safe_load(text)


def parse_template_header(template_path: str | Path) -> dict[str, Any]:
    """Extract the YAML doc block at the top of a template file (between '# ---' lines).

    Templates declare their parameters and metadata in a leading YAML block:

      # ---
      # description: Foo bar
      # parameters:
      #   product: { type: product_ref, required: true }
      # ---
      id: ...
    """
    text = Path(template_path).read_text()
    lines = text.splitlines()
    if not lines or not lines[0].strip().startswith("# ---"):
        return {}
    body: list[str] = []
    started = False
    for line in lines:
        stripped = line.strip()
        if stripped == "# ---":
            if not started:
                started = True
                continue
            break
        if started:
            if line.startswith("# "):
                body.append(line[2:])
            elif line.startswith("#"):
                body.append(line[1:].lstrip())
    if not body:
        return {}
    return yaml.safe_load("\n".join(body)) or {}
