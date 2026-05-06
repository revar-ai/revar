# SPDX-License-Identifier: Apache-2.0
"""Run a task with the screenshot-only vision baseline (GPT-4o)."""

from __future__ import annotations

import asyncio
import os
import sys

from revar import Environment, Runner, Task
from revar.adapters.vision_baseline import VisionBaselineAdapter


async def main(task_path: str) -> int:
    task = Task.from_yaml(task_path)
    headed = os.environ.get("REVAR_HEADED", "").lower() in ("1", "true", "yes")
    env = Environment(site=task.site)
    runner = Runner(env)
    result = await runner.run(agent=VisionBaselineAdapter(), task=task, headless=not headed)
    print(f"passed={result.eval.passed} reason={result.eval.reason}")
    for k, v in result.metrics.items():
        print(f"  {k}: {v}")
    return 0 if result.eval.passed else 1


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    sys.exit(asyncio.run(main(sys.argv[1])))
