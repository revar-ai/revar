# SPDX-License-Identifier: Apache-2.0
"""Scripted reference: discovers Lumen Smart Bulb is OOS, picks an alternative
home-category product, and completes checkout."""

from __future__ import annotations

import time

from resurf.adapters.base import AdapterResult
from resurf.trajectory import Step, Trajectory


async def run(*, task, env, context, trajectory: Trajectory) -> AdapterResult:
    page = await context.new_page()

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

    # See the OOS state on PDP
    await page.goto(env.base_url + "/products/lumen-smart-bulb")
    step(0, "nav", {"url": page.url})

    # Pick another home product instead (TrailMate Water Bottle is in 'outdoors',
    # so we'll choose something else from /products?category=home if any are in stock,
    # otherwise fall back to a known in-stock product).
    await page.goto(env.base_url + "/products?category=home")
    step(1, "nav", {"url": page.url})

    # Click the first product card we can find that doesn't say "Out of stock"
    cards = page.locator("article[data-product-slug]")
    count = await cards.count()
    chosen = None
    for i in range(count):
        card = cards.nth(i)
        text = await card.inner_text()
        if "Out of stock" in text:
            continue
        slug = await card.get_attribute("data-product-slug")
        if slug:
            chosen = slug
            break

    if chosen is None:
        # Fall back to a known in-stock product
        chosen = "trailmate-water-bottle"

    await page.goto(env.base_url + f"/products/{chosen}")
    step(2, "nav", {"url": page.url, "chosen": chosen})

    await page.get_by_role("button", name="Add to cart").click()
    step(3, "click", {"selector": "Add to cart"})

    await page.goto(env.base_url + "/checkout")
    await page.wait_for_url("**/checkout/shipping**")
    await page.get_by_role("button", name="Save and continue to review").click()
    await page.wait_for_url("**/checkout/review**")
    step(4, "nav+click", {"step": "shipping"})

    await page.get_by_role("button", name="Continue to payment").click()
    await page.wait_for_url("**/checkout/confirm**")
    step(5, "click", {"selector": "Continue to payment"})

    await page.locator("#card_number").fill("4242 4242 4242 4242")
    await page.locator("#card_exp").fill("12/30")
    await page.locator("#card_cvc").fill("123")
    await page.get_by_role("button", name="Place order").click()
    await page.wait_for_url("**/checkout/confirmation/**", timeout=15_000)
    step(6, "click", {"selector": "Place order"})

    return AdapterResult(actions_taken=7)
