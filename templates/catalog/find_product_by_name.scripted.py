# SPDX-License-Identifier: Apache-2.0
"""Scripted reference trajectory for find_product_by_name.

Demonstrates the simplest possible interaction: navigate, search, click result.
Used by `resurf task try` to prove tasks generated from this template
are solvable end-to-end (and as an upper-bound trajectory for token/step
baselining once real agents arrive).
"""

from __future__ import annotations

import time

from resurf.adapters.base import AdapterResult
from resurf.trajectory import Step, Trajectory


async def run(*, task, env, context, trajectory: Trajectory) -> AdapterResult:
    page = await context.new_page()

    product_name = task.parameters["product_name"]
    product_slug = task.parameters["product_slug"]

    t0 = time.time()
    await page.goto(env.base_url + "/")
    trajectory.append(
        Step(
            index=0,
            timestamp=time.time(),
            action_type="nav",
            action={"url": env.base_url + "/"},
            url=page.url,
            title=await page.title(),
            latency_ms=(time.time() - t0) * 1000,
        )
    )

    # Use the header search field (label: "Search products")
    t0 = time.time()
    await page.get_by_label("Search products").first.fill(product_name)
    await page.get_by_label("Search products").first.press("Enter")
    await page.wait_for_url("**/search**")
    trajectory.append(
        Step(
            index=1,
            timestamp=time.time(),
            action_type="type",
            action={"target": "Search products", "text": product_name},
            url=page.url,
            latency_ms=(time.time() - t0) * 1000,
        )
    )

    # Click the matching product card (links to /products/<slug>)
    t0 = time.time()
    await page.locator(f'a[href="/products/{product_slug}"]').first.click()
    await page.wait_for_url(f"**/products/{product_slug}")
    trajectory.append(
        Step(
            index=2,
            timestamp=time.time(),
            action_type="click",
            action={"selector": f'a[href="/products/{product_slug}"]'},
            url=page.url,
            title=await page.title(),
            latency_ms=(time.time() - t0) * 1000,
        )
    )

    return AdapterResult(actions_taken=3)
