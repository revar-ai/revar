# SPDX-License-Identifier: Apache-2.0
"""Vision baseline adapter (single-screenshot per step, GPT-4o function calling).

This is intentionally minimal — its purpose is to give a reference number for
how a "screenshot-and-click-coords" agent performs on shop_v1, not to be a
high-quality general agent. It demonstrates the Adapter contract for vision-
only agents and is useful as a control in correlation studies.
"""

from __future__ import annotations

import base64
import json
import os
import time
from dataclasses import dataclass

from .base import Adapter, AdapterResult

SYSTEM_PROMPT = """You control a web browser by issuing ONE action per turn.
Available actions (return strict JSON, nothing else):
  {"action": "nav", "url": "<absolute or path>"}
  {"action": "click", "x": <int>, "y": <int>}
  {"action": "type", "text": "<string>"}
  {"action": "press", "key": "Enter"}
  {"action": "scroll", "dy": <int>}
  {"action": "done"}      # task complete
  {"action": "give_up", "reason": "<why>"}
The user message contains the current goal and a screenshot. Reason briefly,
then output ONLY the JSON action."""


@dataclass
class VisionBaselineAdapter(Adapter):
    name: str = "vision_baseline"
    model: str = "gpt-4o"
    max_steps: int | None = None

    async def run(self, *, task, env, context, trajectory) -> AdapterResult:
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "openai is not installed. Install with `pip install 'revar[vision]'`."
            ) from exc

        client = OpenAI()
        page = await context.new_page()
        await page.goto(env.base_url + "/")

        from revar.trajectory import Step

        max_steps = self.max_steps or task.budget.max_steps
        tokens_in = 0
        tokens_out = 0
        actions = 0
        # Stream actions to stdout so you can watch the agent reason in real
        # time (and see when it's stuck in a loop). Off by default; opt in
        # with REVAR_DEBUG=1 to keep CI logs clean.
        verbose = os.environ.get("REVAR_DEBUG", "").lower() in ("1", "true", "yes")

        for i in range(max_steps):
            shot_bytes = await page.screenshot(type="png", full_page=False)
            shot_b64 = base64.b64encode(shot_bytes).decode()
            url = page.url

            user_content = [
                {"type": "text", "text": f"Goal: {task.goal.strip()}\nCurrent URL: {url}"},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{shot_b64}"}},
            ]
            response = client.chat.completions.create(
                model=self.model,
                temperature=0,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_content},
                ],
            )
            usage = response.usage
            if usage is not None:
                tokens_in += usage.prompt_tokens or 0
                tokens_out += usage.completion_tokens or 0

            content = response.choices[0].message.content or ""
            try:
                # Find the first JSON object in the response
                start = content.find("{")
                end = content.rfind("}")
                action = json.loads(content[start : end + 1])
            except Exception:
                trajectory.append(
                    Step(
                        index=i,
                        timestamp=time.time(),
                        action_type="error",
                        action={"raw": content[:500]},
                        url=url,
                        note="failed_to_parse_action",
                        tokens_in=usage.prompt_tokens if usage else 0,
                        tokens_out=usage.completion_tokens if usage else 0,
                    )
                )
                break

            actions += 1
            atype = action.get("action", "other")
            if verbose:
                summary = {k: v for k, v in action.items() if k != "action"}
                print(
                    f"[vision_baseline] step {i + 1}/{max_steps}: {atype} {summary} @ {url}",
                    flush=True,
                )
            try:
                if atype == "nav":
                    target = action.get("url", "/")
                    if not target.startswith("http"):
                        target = env.base_url + (target if target.startswith("/") else "/" + target)
                    await page.goto(target)
                elif atype == "click":
                    await page.mouse.click(int(action["x"]), int(action["y"]))
                elif atype == "type":
                    await page.keyboard.type(action.get("text", ""))
                elif atype == "press":
                    await page.keyboard.press(action.get("key", "Enter"))
                elif atype == "scroll":
                    await page.mouse.wheel(0, int(action.get("dy", 400)))
                elif atype in ("done", "give_up"):
                    trajectory.append(
                        Step(
                            index=i,
                            timestamp=time.time(),
                            action_type=atype,
                            action=action,
                            url=url,
                            tokens_in=usage.prompt_tokens if usage else 0,
                            tokens_out=usage.completion_tokens if usage else 0,
                        )
                    )
                    break
            except Exception as exc:
                trajectory.append(
                    Step(
                        index=i,
                        timestamp=time.time(),
                        action_type="error",
                        action={**action, "exc": str(exc)},
                        url=url,
                        tokens_in=usage.prompt_tokens if usage else 0,
                        tokens_out=usage.completion_tokens if usage else 0,
                    )
                )
                break

            trajectory.append(
                Step(
                    index=i,
                    timestamp=time.time(),
                    action_type=atype,
                    action=action,
                    url=url,
                    tokens_in=usage.prompt_tokens if usage else 0,
                    tokens_out=usage.completion_tokens if usage else 0,
                )
            )

        return AdapterResult(
            actions_taken=actions,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            notes={"model": self.model},
        )
