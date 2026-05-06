# SPDX-License-Identifier: Apache-2.0
"""revar command-line interface.

Subcommands:
  task list                      List bundled tasks
  task validate <path>           Schema + live-site validation
  task new                       Interactive scaffold
  task from-template <name> ...  Render a template into a concrete task YAML
  task try <path>                Run the scripted reference trajectory (smoke test)
  env reset / configure / state  Drive admin endpoints (handy from shell)
"""

from __future__ import annotations

import asyncio
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import click
import httpx
import yaml
from rich.console import Console
from rich.table import Table

from .env import Environment
from .task import Task, validate_task_dict
from .templating import parse_template_header, render_template_to_dict

console = Console()


def _default_base_url() -> str:
    import os

    return os.environ.get("REVAR_BASE_URL", "http://localhost:8080")


def _resolve_repo_root() -> Path:
    """Walk up from CWD to find the repo root (a dir containing tasks/ or pyproject.toml)."""
    here = Path.cwd()
    for parent in [here, *here.parents]:
        if (parent / "tasks").is_dir() and (parent / "templates").is_dir():
            return parent
    return here


@click.group()
@click.version_option(package_name="revar")
def main() -> None:
    """revar CLI."""


# ---------------------------------------------------------------------------
# Task subcommands
# ---------------------------------------------------------------------------


@main.group()
def task() -> None:
    """Task authoring and validation."""


@task.command("list")
@click.option("--root", default=None, help="Tasks directory (default: ./tasks)")
def task_list(root: str | None) -> None:
    base = Path(root) if root else _resolve_repo_root() / "tasks"
    if not base.exists():
        click.echo(f"No tasks directory at {base}", err=True)
        sys.exit(2)
    rows = []
    for path in sorted(base.rglob("*.yaml")):
        try:
            data = yaml.safe_load(path.read_text())
            rows.append(
                (
                    data.get("id", "?"),
                    data.get("category", "?"),
                    data.get("hardness", "?"),
                    str(path.relative_to(base.parent)),
                )
            )
        except Exception as exc:  # noqa: BLE001
            rows.append(("INVALID", "?", "?", f"{path}: {exc}"))
    table = Table(title=f"Tasks under {base}")
    table.add_column("id")
    table.add_column("category")
    table.add_column("hardness")
    table.add_column("path")
    for r in rows:
        table.add_row(*r)
    console.print(table)


@task.command("validate")
@click.argument("path", type=click.Path(exists=True, dir_okay=False))
@click.option("--base-url", default=None, help="Site base URL for live-site checks")
@click.option("--skip-live", is_flag=True, help="Skip live-site checks")
def task_validate(path: str, base_url: str | None, skip_live: bool) -> None:
    p = Path(path)
    data = yaml.safe_load(p.read_text())
    try:
        validate_task_dict(data)
    except ValueError as exc:
        console.print(f"[red]Schema invalid:[/red]\n{exc}")
        sys.exit(1)
    console.print("[green]Schema valid[/green]")

    if skip_live:
        return

    url = base_url or _default_base_url()
    try:
        r = httpx.get(f"{url}/api/health", timeout=5)
        r.raise_for_status()
    except Exception as exc:  # noqa: BLE001
        console.print(f"[yellow]Live-site checks skipped (site unreachable at {url}: {exc})[/yellow]")
        return

    env = Environment(site=data["site"], base_url=url)
    env.reset(seed=data.get("seed", 42))
    env.configure(data.get("modifiers") or {})

    # Try the success query so we'd notice obvious typos
    success = data["success"]
    if success.get("type") == "state_predicate":
        from .runtime import substitute_bindings

        sql = substitute_bindings(success["query"], env.default_bindings())
        try:
            env.query(sql)
            console.print("[green]success.query parses and runs against fresh DB[/green]")
        except RuntimeError as exc:
            console.print(f"[red]success.query failed:[/red] {exc}")
            sys.exit(1)
    elif success.get("type") == "python":
        spec = importlib.util.find_spec(success["module"])
        if spec is None:
            console.print(f"[red]success.module not importable:[/red] {success['module']}")
            sys.exit(1)
        console.print("[green]success.module imports cleanly[/green]")

    console.print("[green]All checks passed[/green]")


@task.command("from-template")
@click.argument("name")
@click.option("--out", "out_dir", required=True, type=click.Path(file_okay=False))
@click.option("--root", default=None, help="Templates root (default: ./templates)")
@click.option(
    "--param",
    "-p",
    multiple=True,
    help="Parameter as key=value (repeat). Values parsed as YAML scalars.",
)
def task_from_template(name: str, out_dir: str, root: str | None, param: tuple[str, ...]) -> None:
    repo = _resolve_repo_root()
    templates_root = Path(root) if root else repo / "templates"
    template_path = templates_root / f"{name}.yaml.j2"
    if not template_path.exists():
        console.print(f"[red]Template not found:[/red] {template_path}")
        sys.exit(2)

    header = parse_template_header(template_path)
    declared = (header.get("parameters") or {}) if isinstance(header, dict) else {}

    ctx: dict[str, Any] = {}
    for raw in param:
        if "=" not in raw:
            console.print(f"[red]Bad --param (expected key=value):[/red] {raw}")
            sys.exit(2)
        k, v = raw.split("=", 1)
        ctx[k.strip()] = yaml.safe_load(v)

    missing = [k for k, spec in declared.items() if isinstance(spec, dict) and spec.get("required") and k not in ctx]
    if missing:
        console.print(f"[red]Missing required parameters:[/red] {', '.join(missing)}")
        sys.exit(2)

    data = render_template_to_dict(template_path, ctx)
    try:
        validate_task_dict(data)
    except ValueError as exc:
        console.print(f"[red]Generated task failed schema validation:[/red]\n{exc}")
        sys.exit(1)

    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    filename = data["id"].split(".")[-1] + ".yaml"
    target = out_path / filename
    target.write_text(yaml.safe_dump(data, sort_keys=False))
    console.print(f"[green]Wrote[/green] {target}")


@task.command("try")
@click.argument("path", type=click.Path(exists=True, dir_okay=False))
@click.option("--base-url", default=None)
@click.option("--headed", is_flag=True, help="Run with a visible browser window")
def task_try(path: str, base_url: str | None, headed: bool) -> None:
    """Run the scripted reference trajectory for this task as a smoke test."""
    repo = _resolve_repo_root()
    task = Task.from_yaml(path)

    # Find the scripted reference trajectory: same name as the template the task was generated from,
    # else look for a `<task-id>.scripted.py` next to the YAML file.
    candidates: list[Path] = []
    if task.source_path:
        candidates.append(task.source_path.with_suffix(".scripted.py"))
    leaf = task.id.split(".")[-1]
    candidates.extend(
        [
            repo / "templates" / task.category / f"{leaf}.scripted.py",
            *list((repo / "templates").rglob(f"{leaf}.scripted.py")),
        ]
    )
    scripted: Path | None = next((c for c in candidates if c.exists()), None)
    if scripted is None:
        console.print(
            "[yellow]No scripted reference trajectory found.[/yellow] "
            "Looked at:\n  " + "\n  ".join(str(c) for c in candidates),
        )
        sys.exit(2)

    spec = importlib.util.spec_from_file_location("_revar_scripted", scripted)
    if spec is None or spec.loader is None:
        console.print(f"[red]Could not load scripted trajectory:[/red] {scripted}")
        sys.exit(2)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if not hasattr(module, "run"):
        console.print(f"[red]{scripted} must define an async run(task, env, context, trajectory) function[/red]")
        sys.exit(2)

    from .adapters.base import Adapter, AdapterResult
    from .runner import Runner

    class _ScriptedAdapter(Adapter):
        name = f"scripted:{leaf}"

        async def run(self, *, task, env, context, trajectory):
            return await module.run(task=task, env=env, context=context, trajectory=trajectory)

    env = Environment(site=task.site, base_url=base_url or _default_base_url())
    runner = Runner(env)
    result = asyncio.run(runner.run(agent=_ScriptedAdapter(), task=task, headless=not headed))

    table = Table(title=f"task try: {task.id}")
    for k, v in result.metrics.items():
        table.add_row(str(k), str(v))
    console.print(table)
    if not result.eval.passed:
        console.print(f"[red]Task did not pass:[/red] {result.eval.reason}")
        sys.exit(1)
    console.print("[green]Task is solvable[/green]")


@task.command("new")
@click.option("--site", default="shop_v1")
@click.option("--category", required=True, type=click.Choice(["find", "cart", "checkout", "account", "multistep", "adversarial", "mobile"]))
@click.option("--from-template", "from_tmpl", default=None, help="Template to start from")
@click.option("--out", "out_dir", required=True, type=click.Path(file_okay=False))
def task_new(site: str, category: str, from_tmpl: str | None, out_dir: str) -> None:
    """Stub interactive scaffolder. v0 ships with --from-template; full prompts in v1."""
    if from_tmpl is None:
        console.print(
            "[yellow]Interactive prompts will land in v1.[/yellow] "
            "For now, pass --from-template <category>/<name>."
        )
        sys.exit(2)
    ctx_obj = click.get_current_context().invoke
    ctx_obj(task_from_template, name=from_tmpl, out_dir=out_dir, root=None, param=())


# ---------------------------------------------------------------------------
# Env subcommands (utility wrappers)
# ---------------------------------------------------------------------------


@main.group()
def env() -> None:
    """Drive site admin endpoints (reset, configure, state)."""


@env.command("reset")
@click.option("--seed", default=42)
@click.option("--base-url", default=None)
def env_reset(seed: int, base_url: str | None) -> None:
    e = Environment(site="shop_v1", base_url=base_url or _default_base_url())
    out = e.reset(seed=seed)
    console.print_json(data=out)


@env.command("configure")
@click.argument("kvs", nargs=-1)
@click.option("--base-url", default=None)
def env_configure(kvs: tuple[str, ...], base_url: str | None) -> None:
    payload: dict[str, Any] = {}
    for kv in kvs:
        if "=" not in kv:
            console.print(f"[red]Expected key=value:[/red] {kv}")
            sys.exit(2)
        k, v = kv.split("=", 1)
        payload[k.strip()] = yaml.safe_load(v)
    e = Environment(site="shop_v1", base_url=base_url or _default_base_url())
    out = e.configure(payload)
    console.print_json(data=out)


@env.command("state")
@click.option("--table", default=None)
@click.option("--base-url", default=None)
def env_state(table: str | None, base_url: str | None) -> None:
    e = Environment(site="shop_v1", base_url=base_url or _default_base_url())
    out = e.state(table)
    console.print_json(data=out)


if __name__ == "__main__":
    main()
