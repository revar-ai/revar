# SPDX-License-Identifier: Apache-2.0
"""Scripted reference: correctly clicks 'Add to cart' (not 'Buy now') and
navigates to /cart afterward."""

from __future__ import annotations

import time

from resurf.adapters.base import AdapterResult
from resurf.trajectory import Step, Trajectory


async def run(*, task, env, context, trajectory: Trajectory) -> AdapterResult:
    page = await context.new_page()
    p = task.parameters

    def step(idx, action_type, action):
        trajectory.append(
            Step(
                index=idx,
                timestamp=time.time(),
                action_type=action_type,
                action=action,
                url=page.url,
            )
        )

    await page.goto(env.base_url + f"/products/{p['product_slug']}")
    step(0, "nav", {"url": page.url})

    if int(p["qty"]) != 1:
        await page.locator("#qty").fill(str(p["qty"]))
        step(1, "type", {"selector": "#qty", "text": str(p["qty"])})

    # CORRECT button (not "Buy now")
    await page.get_by_role("button", name="Add to cart").click()
    step(2, "click", {"selector": 'button[aria-label="Add to cart"]'})

    await page.goto(env.base_url + "/cart")
    step(3, "nav", {"url": page.url})

    return AdapterResult(actions_taken=4)
