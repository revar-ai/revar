# SPDX-License-Identifier: Apache-2.0
"""Stagehand adapter (via Node subprocess).

Stagehand is a Node.js framework. We invoke it via a small Node bridge script
using JSON-RPC-over-stdio. The bridge script lives at
`adapters/stagehand/bridge.mjs` in the repo and is shipped with resurf;
users need Node 20+ on PATH but no Python-side `stagehand` install.

We do NOT take over the Playwright context here — Stagehand owns its own
browser (it integrates tightly with Playwright internally). For tasks that
require pre-auth, we forward the seeded session cookie via Stagehand's CDP
init; for v0 those tasks are out of scope for this adapter and we recommend
browser-use instead.
"""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import time
from dataclasses import dataclass
from pathlib import Path

from .base import Adapter, AdapterResult


@dataclass
class StagehandAdapter(Adapter):
    name: str = "stagehand"
    bridge_path: str | None = None
    node_bin: str = "node"
    model: str = "gpt-4o"
    headless: bool = True

    async def run(self, *, task, env, context, trajectory) -> AdapterResult:
        if shutil.which(self.node_bin) is None:
            raise RuntimeError(
                f"Node binary `{self.node_bin}` not on PATH. "
                "Install Node 20+ to use the Stagehand adapter."
            )

        bridge = Path(self.bridge_path) if self.bridge_path else _default_bridge_path()
        if not bridge.exists():
            raise RuntimeError(
                f"Stagehand bridge not found at {bridge}. "
                "It should ship in adapters/stagehand/bridge.mjs."
            )
        if not os.environ.get("OPENAI_API_KEY"):
            raise RuntimeError("OPENAI_API_KEY is not set; required by Stagehand.")

        request = {
            "goal": task.goal.strip(),
            "base_url": env.base_url,
            "model": self.model,
            "max_steps": task.budget.max_steps,
            "viewport": task.viewport,
            "headless": self.headless,
        }
        if task.user_credentials:
            request["credentials"] = task.user_credentials

        proc = await asyncio.create_subprocess_exec(
            self.node_bin,
            str(bridge),
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate(input=(json.dumps(request) + "\n").encode())

        # The bridge writes its error JSON to stdout (so we can recover a
        # structured ``error`` field) and exits non-zero. Try to parse stdout
        # FIRST so we surface a useful message; fall back to stderr only if
        # stdout is empty/unparseable.
        from resurf.trajectory import Step

        payload: dict | None = None
        parse_err: Exception | None = None
        if stdout:
            try:
                payload = json.loads(stdout.decode().splitlines()[-1])
            except Exception as exc:
                parse_err = exc

        if proc.returncode != 0:
            bridge_error = (payload or {}).get("error") if payload else None
            stderr_text = stderr.decode(errors="replace").strip()
            hint = ""
            if proc.returncode == 2 and not bridge_error:
                hint = (
                    " (exit 2 typically means Stagehand isn't installed — "
                    "run `cd adapters/stagehand && npm install @browserbasehq/stagehand`)"
                )
            raise RuntimeError(
                "Stagehand bridge exited with code "
                f"{proc.returncode}.{hint}\n"
                f"  bridge_error: {bridge_error!r}\n"
                f"  stderr: {stderr_text!r}"
            )

        if payload is None:
            raise RuntimeError(
                f"Could not parse stagehand bridge output: {parse_err}\n"
                f"stdout={stdout!r}\nstderr={stderr!r}"
            )

        for i, item in enumerate(payload.get("steps") or []):
            trajectory.append(
                Step(
                    index=i,
                    timestamp=time.time(),
                    action_type=item.get("type", "stagehand_action"),
                    action=item.get("action", {}),
                    url=item.get("url"),
                    tokens_in=item.get("tokens_in", 0),
                    tokens_out=item.get("tokens_out", 0),
                )
            )

        return AdapterResult(
            actions_taken=len(payload.get("steps") or []),
            tokens_in=int(payload.get("tokens_in", 0)),
            tokens_out=int(payload.get("tokens_out", 0)),
            notes={"model": self.model},
        )


def _default_bridge_path() -> Path:
    """Walk upward from this file looking for adapters/stagehand/bridge.mjs."""
    here = Path(__file__).resolve()
    for parent in [here.parent, *here.parents]:
        candidate = parent / "adapters" / "stagehand" / "bridge.mjs"
        if candidate.exists():
            return candidate
    return Path("adapters/stagehand/bridge.mjs")
