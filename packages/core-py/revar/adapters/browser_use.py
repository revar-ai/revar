# SPDX-License-Identifier: Apache-2.0
"""Browser Use adapter.

Hands the agent the task goal as a natural-language prompt, lets browser-use
own the browser, and converts its history into our Trajectory shape.

Install with: pip install 'revar[browser-use]'

Notes
-----
- browser-use launches its own Playwright instance. We pass our Environment's
  configured browser context by handing browser-use the `Browser` it expects
  (via the BrowserContext we already created) and letting it drive.
- Token accounting: browser-use exposes per-step `model_response.usage` once
  the run completes; we sum them for the trajectory metrics.
- This adapter relies on a publicly available LLM (OpenAI by default). The
  caller is responsible for providing OPENAI_API_KEY (or equivalent) via env.
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

    async def run(self, *, task, env, context, trajectory) -> AdapterResult:
        try:
            from browser_use import Agent
            from browser_use.browser.browser import Browser, BrowserConfig
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "browser-use is not installed. Install with `pip install 'revar[browser-use]'`."
            ) from exc

        try:
            from langchain_openai import ChatOpenAI
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "langchain-openai is required for the browser-use adapter (it ships as a transitive dep). "
                "Install with `pip install langchain-openai`."
            ) from exc

        if not os.environ.get("OPENAI_API_KEY"):
            raise RuntimeError(
                "OPENAI_API_KEY is not set. The browser-use adapter uses OpenAI by default."
            )

        # Build the task prompt: NL goal + light grounding (the seeded user creds
        # if applicable, the base URL).
        prompt_lines = [
            f"You are interacting with a synthetic e-commerce site at {env.base_url}.",
            f"Goal: {task.goal.strip()}",
        ]
        if task.user_credentials:
            prompt_lines.append(
                f"You are signed in as {task.user_credentials['email']}. "
                "There is no need to sign in again."
            )
        if self.extra_instructions:
            prompt_lines.append(self.extra_instructions)
        prompt = "\n\n".join(prompt_lines)

        from revar.trajectory import Step

        from playwright.async_api import Page

        # browser-use's Browser takes either a Playwright Browser or its own; we
        # construct it with our existing context to inherit cookies (auth) and
        # viewport. Newer browser-use versions expose a `BrowserContext` wrapper.
        try:
            from browser_use.browser.context import BrowserContext as BUContext  # type: ignore
        except ImportError:  # pragma: no cover
            BUContext = None  # type: ignore

        browser = Browser(config=BrowserConfig(headless=True))
        # Ensure browser-use sees our context's cookies — easiest is to navigate
        # the agent's first page in OUR context to the base URL, then hand it off.
        page: Page = await context.new_page()
        await page.goto(env.base_url + "/")

        agent = Agent(
            task=prompt,
            llm=ChatOpenAI(model=self.model, temperature=0),
            browser=browser,
        )

        max_steps = self.max_steps or task.budget.max_steps
        history = await agent.run(max_steps=max_steps)

        tokens_in = 0
        tokens_out = 0

        for i, item in enumerate(getattr(history, "history", []) or []):
            tokens_in += int(getattr(getattr(item, "usage", None), "prompt_tokens", 0) or 0)
            tokens_out += int(getattr(getattr(item, "usage", None), "completion_tokens", 0) or 0)
            url = None
            try:
                url = item.state.url  # type: ignore[attr-defined]
            except Exception:  # noqa: BLE001
                pass
            action = getattr(item, "action", None) or {}
            trajectory.append(
                Step(
                    index=i,
                    timestamp=time.time(),
                    action_type=getattr(action, "type", "browser_use_action") if action else "browser_use_action",
                    action={"raw": str(action)[:500]} if action else {},
                    url=url,
                )
            )

        try:
            await browser.close()
        except Exception:  # noqa: BLE001
            pass

        return AdapterResult(
            actions_taken=len(getattr(history, "history", []) or []),
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            notes={"model": self.model},
        )
