# SPDX-License-Identifier: Apache-2.0
"""Scripted reference trajectory: buy N of a product, apply coupon at checkout,
ship to default address, pay with a test card."""

from __future__ import annotations

import time

from revar.adapters.base import AdapterResult
from revar.trajectory import Step, Trajectory


async def run(*, task, env, context, trajectory: Trajectory) -> AdapterResult:
    page = await context.new_page()
    p = task.parameters
    slug = p["product_slug"]
    qty = int(p["qty"])
    coupon = p["coupon"]

    def step(idx, action_type, action, latency_ms=None):
        trajectory.append(
            Step(
                index=idx,
                timestamp=time.time(),
                action_type=action_type,
                action=action,
                url=page.url,
                latency_ms=latency_ms,
            )
        )

    # Open the PDP
    await page.goto(env.base_url + f"/products/{slug}")
    step(0, "nav", {"url": page.url})

    # Set quantity
    await page.locator("#qty").fill(str(qty))
    step(1, "type", {"selector": "#qty", "text": str(qty)})

    # Add to cart
    await page.get_by_role("button", name="Add to cart").click()
    step(2, "click", {"selector": 'button[aria-label="Add to cart"]'})

    # Go to checkout
    await page.goto(env.base_url + "/checkout")
    step(3, "nav", {"url": page.url})

    # Wait for shipping step (auto-redirected from /checkout)
    await page.wait_for_url("**/checkout/shipping**")

    # Save and continue (default address pre-selected)
    await page.get_by_role("button", name="Save and continue to review").click()
    await page.wait_for_url("**/checkout/review**")
    step(4, "click", {"selector": "Save and continue"})

    # Apply coupon at checkout (the *real* one)
    await page.get_by_label("Promo code (checkout)").fill(coupon)
    await page.get_by_role("button", name="Apply checkout promo code").click()
    step(5, "type+click", {"coupon": coupon})

    # Continue to payment
    await page.get_by_role("button", name="Continue to payment").click()
    await page.wait_for_url("**/checkout/confirm**")
    step(6, "click", {"selector": "Continue to payment"})

    # Fill card details and submit
    await page.locator("#card_number").fill("4242 4242 4242 4242")
    await page.locator("#card_exp").fill("12/30")
    await page.locator("#card_cvc").fill("123")
    step(7, "type", {"card": "4242…4242"})

    await page.get_by_role("button", name="Place order").click()
    # Wait for either confirmation or an error toast
    await page.wait_for_url("**/checkout/confirmation/**", timeout=15_000)
    step(8, "click", {"selector": "Place order"})

    return AdapterResult(actions_taken=9)
