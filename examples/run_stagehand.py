# SPDX-License-Identifier: Apache-2.0
"""Run a single task with the Stagehand adapter against a local shop_v1.

Stagehand is a Node.js framework, so this example shells out to
adapters/stagehand/bridge.mjs over stdio. Requirements:

    Node 20+ on PATH
    npm install @browserbasehq/stagehand   # run inside adapters/stagehand/
    export OPENAI_API_KEY=sk-...

Usage:
    docker compose up -d shop_v1
    python examples/run_stagehand.py tasks/shop_v1/find/find_acme_bluetooth_speaker.yaml
"""

from __future__ import annotations

import asyncio
import sys

from revar import Environment, Runner, Task
from revar.adapters.stagehand import StagehandAdapter


async def main(task_path: str) -> int:
    task = Task.from_yaml(task_path)
    env = Environment(site=task.site)
    health = env.health()
    print(f"[revar] site healthy: {health.get('ok')}")
    print(f"[revar] running stagehand on {task.id}")

    runner = Runner(env)
    result = await runner.run(agent=StagehandAdapter(), task=task)

    print()
    print(f"[revar] passed={result.eval.passed}  reason={result.eval.reason}")
    for k, v in result.metrics.items():
        print(f"[revar]   {k}: {v}")
    return 0 if result.eval.passed else 1


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    sys.exit(asyncio.run(main(sys.argv[1])))
