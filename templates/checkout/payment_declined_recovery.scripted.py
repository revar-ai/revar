# SPDX-License-Identifier: Apache-2.0
"""Scripted reference: handles the first 'card declined' error, retries with a
different card, and completes the order on the second attempt."""

from __future__ import annotations

import time

from revar.adapters.base import AdapterResult
from revar.trajectory import Step, Trajectory


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

    await page.get_by_role("button", name="Add to cart").click()
    step(1, "click", {"selector": "Add to cart"})

    await page.goto(env.base_url + "/checkout")
    await page.wait_for_url("**/checkout/shipping**")
    await page.get_by_role("button", name="Save and continue to review").click()
    await page.wait_for_url("**/checkout/review**")
    step(2, "nav+click", {"step": "shipping"})

    await page.get_by_role("button", name="Continue to payment").click()
    await page.wait_for_url("**/checkout/confirm**")
    step(3, "click", {"selector": "Continue to payment"})

    # First attempt — will be declined
    await page.locator("#card_number").fill("4000 0000 0000 9995")
    await page.locator("#card_exp").fill("12/30")
    await page.locator("#card_cvc").fill("123")
    await page.get_by_role("button", name="Place order").click()
    # Wait for the declined alert to surface
    await page.get_by_role("alert").wait_for(state="visible", timeout=10_000)
    step(4, "click", {"attempt": 1, "result": "declined"})

    # Second attempt — different card; modifier sequence flips to success
    await page.locator("#card_number").fill("4242 4242 4242 4242")
    await page.locator("#card_exp").fill("12/30")
    await page.locator("#card_cvc").fill("123")
    await page.get_by_role("button", name="Place order").click()
    await page.wait_for_url("**/checkout/confirmation/**", timeout=15_000)
    step(5, "click", {"attempt": 2, "result": "paid"})

    return AdapterResult(actions_taken=6)
