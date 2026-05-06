# SPDX-License-Identifier: Apache-2.0
"""Runner: orchestrates env reset, modifier configuration, agent execution, evaluation."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any

from .adapters.base import Adapter, AdapterResult
from .env import Environment
from .task import EvalResult, Task
from .trajectory import Trajectory


@dataclass
class RunResult:
    task: Task
    eval: EvalResult
    trajectory: Trajectory
    adapter_result: AdapterResult | None = None
    metrics: dict[str, Any] = field(default_factory=dict)


class Runner:
    def __init__(self, env: Environment) -> None:
        self.env = env

    async def run(
        self,
        *,
        agent: Adapter,
        task: Task,
        headless: bool = True,
        trajectory_root: str = "trajectories",
    ) -> RunResult:
        # 1. reset DB to seeded snapshot
        self.env.reset(seed=task.seed)
        # 2. apply modifier configuration
        self.env.configure(task.modifiers or {})
        # 3. apply time freeze if requested
        frozen = (task.modifiers or {}).get("frozen_time_iso")
        if frozen is not None:
            self.env.freeze_time(frozen)

        traj = Trajectory.for_task(task.id, agent.name, root=trajectory_root)
        adapter_result: AdapterResult | None = None

        try:
            async with self.env.browser_context(
                viewport=task.viewport,
                headless=headless,
                user_credentials=task.user_credentials,
            ) as ctx:
                budget_s = task.budget.max_wall_clock_s
                adapter_result = await asyncio.wait_for(
                    agent.run(task=task, env=self.env, context=ctx, trajectory=traj),
                    timeout=budget_s + 5,
                )
        except asyncio.TimeoutError:
            traj.append_error(asyncio.TimeoutError(f"exceeded budget {task.budget.max_wall_clock_s}s"))
        except Exception as exc:  # noqa: BLE001
            traj.append_error(exc)

        # Capture final URL from the last recorded step
        final_url = traj.steps[-1].url if traj.steps else None
        traj.finalize(final_url)

        # 4. evaluate
        eval_result = task.evaluate(self.env)

        traj_path = traj.save()
        metrics = {
            "passed": eval_result.passed,
            "reason": eval_result.reason,
            "steps": len(traj.steps),
            "tokens_in": adapter_result.tokens_in if adapter_result else 0,
            "tokens_out": adapter_result.tokens_out if adapter_result else 0,
            "tokens_total": (
                (adapter_result.tokens_in + adapter_result.tokens_out)
                if adapter_result
                else traj.total_tokens
            ),
            "wall_clock_s": traj.duration_s,
            "trajectory_path": str(traj_path),
            "error": traj.error,
        }
        return RunResult(task=task, eval=eval_result, trajectory=traj, adapter_result=adapter_result, metrics=metrics)
