# SPDX-License-Identifier: Apache-2.0
"""Browser Use adapter (v0.12+).

Hands the agent the task goal as a natural-language prompt, lets browser-use
own its browser, and converts its history into our Trajectory shape.

Install with: pip install 'revar[browser-use]'

Compatibility notes
-------------------
- Targets browser-use >= 0.12. The 0.12 line is a hard break from 0.1: it
  bundles its own LLM clients (no more langchain-openai), replaced
  ``BrowserConfig`` with ``BrowserProfile``, and ``Browser`` is now an alias
  for ``BrowserSession``.
- browser-use launches its own browser via CDP. We do NOT hand it the
  Environment's Playwright context (the two are separate). For tasks that
  require pre-auth, we surface the seeded credentials in the task prompt
  and let the agent sign in itself. A future revision can pass a
  ``cdp_url`` to share a launched Chromium between revar and browser-use.
- Token accounting: browser-use exposes per-step usage on
  ``AgentHistoryList.history``; we sum what's available best-effort.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass

from .base import Adapter, AdapterResult


@dataclass
class BrowserUseAdapter(Adapter):
    name: str = "browser-use"
    model: str = "gpt-4o"
    max_steps: int | None = None  # falls back to task.budget.max_steps
    extra_instructions: str = ""
    headless: bool = True

    async def run(self, *, task, env, context, trajectory) -> AdapterResult:
        try:
            from browser_use import (
                Agent,
                BrowserProfile,
                BrowserSession,
                ChatOpenAI,
            )
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "browser-use is not installed. "
                "Install with `pip install 'revar[browser-use]'` "
                "(requires browser-use >= 0.12)."
            ) from exc

        if not os.environ.get("OPENAI_API_KEY"):
            raise RuntimeError(
                "OPENAI_API_KEY is not set. The browser-use adapter uses OpenAI by default."
            )

        prompt_lines = [
            f"You are interacting with a synthetic e-commerce site at {env.base_url}.",
            f"Begin by navigating to {env.base_url}/.",
            f"Goal: {task.goal.strip()}",
        ]
        if task.user_credentials:
            prompt_lines.append(
                f"If you need to sign in, use email '{task.user_credentials['email']}' "
                f"and password '{task.user_credentials['password']}'."
            )
        if self.extra_instructions:
            prompt_lines.append(self.extra_instructions)
        prompt = "\n\n".join(prompt_lines)

        viewport = _viewport_for(task.viewport)
        browser_session = BrowserSession(
            browser_profile=BrowserProfile(
                headless=self.headless,
                viewport=viewport,
            ),
        )

        agent = Agent(
            task=prompt,
            llm=ChatOpenAI(model=self.model, temperature=0),
            browser_session=browser_session,
        )

        max_steps = self.max_steps or task.budget.max_steps
        history = await agent.run(max_steps=max_steps)

        from revar.trajectory import Step

        # Run-level token totals: in v0.12 usage lives on AgentHistoryList,
        # NOT on per-AgentHistory items (they only have StepMetadata for timing).
        # Belt and suspenders: try history.usage first, then fall back to
        # querying the agent's token_cost_service directly (which is what
        # the agent itself uses to populate history.usage).
        run_usage = getattr(history, "usage", None)
        tokens_in = int(getattr(run_usage, "total_prompt_tokens", 0) or 0)
        tokens_out = int(getattr(run_usage, "total_completion_tokens", 0) or 0)

        if tokens_in == 0 and tokens_out == 0:
            try:
                tcs = getattr(agent, "token_cost_service", None)
                if tcs is not None:
                    summary = await tcs.get_usage_summary()
                    tokens_in = int(getattr(summary, "total_prompt_tokens", 0) or 0)
                    tokens_out = int(getattr(summary, "total_completion_tokens", 0) or 0)
                    if os.environ.get("REVAR_DEBUG"):
                        entries = len(getattr(tcs, "usage_history", []) or [])
                        print(
                            f"[revar.browser_use] token_cost_service fallback: "
                            f"entries={entries} prompt={tokens_in} completion={tokens_out}",
                            flush=True,
                        )
            except Exception as exc:  # noqa: BLE001
                if os.environ.get("REVAR_DEBUG"):
                    print(f"[revar.browser_use] token fallback failed: {exc!r}", flush=True)

        if os.environ.get("REVAR_DEBUG"):
            print(
                f"[revar.browser_use] history.usage={run_usage!r} "
                f"final tokens_in={tokens_in} tokens_out={tokens_out}",
                flush=True,
            )

        for i, item in enumerate(getattr(history, "history", []) or []):
            url = None
            try:
                url = item.state.url  # type: ignore[attr-defined]
            except Exception:  # noqa: BLE001
                pass

            # ``model_output.action`` is a list[ActionModel]; pick the first
            # so we have *something* to record. Each ActionModel is a
            # discriminated union of the agent's tool calls (click_element_by_index,
            # input_text, navigate, scroll, done, ...).
            action_obj = None
            try:
                actions = item.model_output.action if item.model_output else []  # type: ignore[attr-defined]
                if actions:
                    action_obj = actions[0]
            except Exception:  # noqa: BLE001
                pass

            action_type = "browser_use_action"
            if action_obj is not None:
                # ActionModel only ever has one field set (the chosen action's name)
                try:
                    dumped = action_obj.model_dump(exclude_none=True)
                    action_type = next(iter(dumped.keys()), "browser_use_action")
                except Exception:  # noqa: BLE001
                    action_type = type(action_obj).__name__

            trajectory.append(
                Step(
                    index=i,
                    timestamp=time.time(),
                    action_type=action_type,
                    action={"raw": str(action_obj)[:500]} if action_obj else {},
                    url=url,
                )
            )

        try:
            await browser_session.kill()  # 0.12 API; falls back to close() below
        except AttributeError:  # pragma: no cover
            try:
                await browser_session.close()
            except Exception:  # noqa: BLE001
                pass
        except Exception:  # noqa: BLE001
            pass

        return AdapterResult(
            actions_taken=len(getattr(history, "history", []) or []),
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            notes={"model": self.model},
        )


def _viewport_for(name: str | None) -> dict[str, int]:
    """Map our task viewport names to browser-use ViewportSize dicts."""
    presets = {
        "desktop": {"width": 1280, "height": 800},
        "mobile_iphone15": {"width": 390, "height": 844},
        "mobile_pixel7": {"width": 412, "height": 915},
    }
    return presets.get(name or "desktop", presets["desktop"])
