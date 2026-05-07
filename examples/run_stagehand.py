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
import os
import sys

from resurf import Environment, Runner, Task
from resurf.adapters.stagehand import StagehandAdapter


async def main(task_path: str) -> int:
    task = Task.from_yaml(task_path)
    env = Environment(site=task.site)
    health = env.health()
    print(f"[resurf] site healthy: {health.get('ok')}")
    print(f"[resurf] running stagehand on {task.id}")

    headed = os.environ.get("REVAR_HEADED", "").lower() in ("1", "true", "yes")
    headless = not headed

    runner = Runner(env)
    result = await runner.run(
        agent=StagehandAdapter(headless=headless),
        task=task,
        headless=headless,
    )

    print()
    print(f"[resurf] passed={result.eval.passed}  reason={result.eval.reason}")
    for k, v in result.metrics.items():
        print(f"[resurf]   {k}: {v}")
    return 0 if result.eval.passed else 1


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    sys.exit(asyncio.run(main(sys.argv[1])))
