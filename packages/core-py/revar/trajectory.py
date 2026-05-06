# SPDX-License-Identifier: Apache-2.0
"""Trajectory recording: per-step actions, screenshots, DOM snapshots, tokens."""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class Step:
    index: int
    timestamp: float
    action_type: str  # nav | click | type | scroll | screenshot | other
    action: dict[str, Any] = field(default_factory=dict)
    url: str | None = None
    title: str | None = None
    tokens_in: int = 0
    tokens_out: int = 0
    latency_ms: float | None = None
    screenshot_path: str | None = None
    dom_snapshot_path: str | None = None
    note: str | None = None


@dataclass
class Trajectory:
    task_id: str
    agent: str
    started_at: float = field(default_factory=time.time)
    ended_at: float | None = None
    steps: list[Step] = field(default_factory=list)
    error: str | None = None
    final_url: str | None = None
    output_dir: Path | None = None

    @classmethod
    def for_task(cls, task_id: str, agent: str, root: str | Path = "trajectories") -> Trajectory:
        ts = datetime.utcfromtimestamp(time.time()).strftime("%Y%m%dT%H%M%S")
        slug = task_id.replace("/", "_").replace(".", "_")
        dirname = Path(root) / f"{ts}_{agent}_{slug}"
        dirname.mkdir(parents=True, exist_ok=True)
        traj = cls(task_id=task_id, agent=agent, output_dir=dirname)
        return traj

    def append(self, step: Step) -> None:
        self.steps.append(step)

    def append_error(self, exc: BaseException) -> None:
        self.error = f"{type(exc).__name__}: {exc}"

    def finalize(self, final_url: str | None) -> None:
        self.ended_at = time.time()
        self.final_url = final_url

    @property
    def duration_s(self) -> float:
        end = self.ended_at if self.ended_at is not None else time.time()
        return max(0.0, end - self.started_at)

    @property
    def total_tokens(self) -> int:
        return sum(s.tokens_in + s.tokens_out for s in self.steps)

    def save(self) -> Path:
        if self.output_dir is None:
            self.output_dir = Path("trajectories") / self.task_id
            self.output_dir.mkdir(parents=True, exist_ok=True)
        path = self.output_dir / "trajectory.json"
        path.write_text(
            json.dumps(
                {
                    "task_id": self.task_id,
                    "agent": self.agent,
                    "started_at": self.started_at,
                    "ended_at": self.ended_at,
                    "duration_s": self.duration_s,
                    "total_tokens": self.total_tokens,
                    "step_count": len(self.steps),
                    "error": self.error,
                    "final_url": self.final_url,
                    "steps": [asdict(s) for s in self.steps],
                },
                indent=2,
                default=str,
            )
        )
        return path
