# SPDX-License-Identifier: Apache-2.0
"""Smoke-run a task using its scripted reference trajectory.

This is what `revar task try` does under the hood. Useful as a
zero-API-key way to confirm a task is wired correctly.
"""

from __future__ import annotations

import asyncio
import importlib.util
import os
import sys
from pathlib import Path

from revar import Environment, Runner, Task
from revar.adapters.base import Adapter


def _resolve_scripted(task: Task) -> Path:
    repo = Path.cwd()
    leaf = task.id.split(".")[-1]
    candidates = list(repo.glob(f"templates/**/{leaf}.scripted.py"))
    if not candidates:
        # try looking up by full id parts (e.g. acme_bluetooth_speaker_q1_summer15)
        candidates = list(repo.glob("templates/**/*.scripted.py"))
        if task.source_path:
            local = task.source_path.with_suffix(".scripted.py")
            if local.exists():
                return local
    if not candidates:
        raise SystemExit("No scripted reference trajectory found in templates/")
    return candidates[0]


async def main(task_path: str) -> int:
    task = Task.from_yaml(task_path)
    scripted = _resolve_scripted(task)
    spec = importlib.util.spec_from_file_location("_scripted", scripted)
    if spec is None or spec.loader is None:
        raise SystemExit(f"Could not load {scripted}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    class _ScriptedAdapter(Adapter):
        name = "scripted"

        async def run(self, *, task, env, context, trajectory):
            return await module.run(task=task, env=env, context=context, trajectory=trajectory)

    headed = os.environ.get("REVAR_HEADED", "").lower() in ("1", "true", "yes")
    env = Environment(site=task.site)
    runner = Runner(env)
    result = await runner.run(agent=_ScriptedAdapter(), task=task, headless=not headed)
    print(f"passed={result.eval.passed} reason={result.eval.reason}")
    for k, v in result.metrics.items():
        print(f"  {k}: {v}")
    return 0 if result.eval.passed else 1


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    sys.exit(asyncio.run(main(sys.argv[1])))
