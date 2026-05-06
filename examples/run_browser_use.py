# SPDX-License-Identifier: Apache-2.0
"""Run a single task with the browser-use adapter against a local shop_v1.

Usage:
    docker compose up -d shop_v1
    export OPENAI_API_KEY=sk-...
    python examples/run_browser_use.py tasks/shop_v1/find/find_acme_bluetooth_speaker.yaml
"""

from __future__ import annotations

import asyncio
import sys

from revar import Environment, Runner, Task
from revar.adapters.browser_use import BrowserUseAdapter


async def main(task_path: str) -> int:
    task = Task.from_yaml(task_path)
    env = Environment(site=task.site)
    health = env.health()
    print(f"[revar] site healthy: {health.get('ok')}")
    print(f"[revar] running browser-use on {task.id}")

    runner = Runner(env)
    result = await runner.run(agent=BrowserUseAdapter(), task=task)

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
