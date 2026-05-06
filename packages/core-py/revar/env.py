# SPDX-License-Identifier: Apache-2.0
"""Environment: the SDK's handle to a running site (e.g. shop_v1).

Responsibilities:
- Drive /__test__/* admin endpoints (reset, configure modifiers, freeze time)
- Run state queries via /__test__/query for success_fn predicates
- Hand the agent a configured Playwright BrowserContext (with pre-auth if requested)
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any

import httpx


@dataclass
class Environment:
    site: str
    base_url: str = "http://localhost:8080"
    timeout_s: float = 60.0

    def __post_init__(self) -> None:
        self._client = httpx.Client(base_url=self.base_url, timeout=self.timeout_s)

    # ------------------------------------------------------------------
    # Admin operations
    # ------------------------------------------------------------------

    def health(self) -> dict[str, Any]:
        r = self._client.get("/api/health")
        r.raise_for_status()
        return r.json()

    def reset(self, seed: int = 42) -> dict[str, Any]:
        r = self._client.post("/__test__/reset", json={"seed": seed})
        r.raise_for_status()
        return r.json()

    def configure(self, modifiers: dict[str, Any]) -> dict[str, Any]:
        # Drop None values so the backend's selective update behaves as expected
        payload = {k: v for k, v in (modifiers or {}).items() if v is not None}
        r = self._client.post("/__test__/configure", json=payload)
        r.raise_for_status()
        return r.json()

    def freeze_time(self, iso: str | None) -> dict[str, Any]:
        r = self._client.post("/__test__/freeze_time", json={"iso": iso})
        r.raise_for_status()
        return r.json()

    # ------------------------------------------------------------------
    # State queries (used by success_fn predicates)
    # ------------------------------------------------------------------

    def query(self, sql: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        r = self._client.post("/__test__/query", json={"sql": sql, "params": params or {}})
        if r.status_code != 200:
            try:
                detail = r.json()
            except Exception:  # noqa: BLE001
                detail = r.text
            raise RuntimeError(f"query failed: {detail}")
        return r.json().get("rows", [])

    def state(self, table: str | None = None) -> dict[str, Any]:
        params = {"table": table} if table else None
        r = self._client.get("/__test__/state", params=params)
        r.raise_for_status()
        return r.json()

    def default_bindings(self) -> dict[str, Any]:
        """Named SQL bindings that tasks reference (e.g. :seeded_user_id)."""
        rows = self.query("SELECT id FROM user WHERE email = 'alex@example.com' LIMIT 1")
        seeded_user_id = rows[0]["id"] if rows else None
        return {"seeded_user_id": seeded_user_id}

    # ------------------------------------------------------------------
    # Agent helpers
    # ------------------------------------------------------------------

    @asynccontextmanager
    async def browser_context(
        self,
        viewport: str = "desktop",
        *,
        headless: bool = True,
        user_credentials: dict[str, str] | None = None,
    ):
        """Yield a Playwright BrowserContext configured for the site.

        If user_credentials is set, performs a real login via /api/auth/login
        (using the API directly, not the UI) and seeds the cookies onto the
        context so the agent starts authenticated. This avoids forcing every
        task to start with a sign-in flow.
        """
        from playwright.async_api import async_playwright

        viewport_map = {
            "desktop": {"width": 1280, "height": 800},
            "mobile_iphone15": {"width": 393, "height": 852},
            "mobile_pixel7": {"width": 412, "height": 915},
        }
        ua_map = {
            "desktop": None,
            "mobile_iphone15": (
                "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) "
                "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1"
            ),
            "mobile_pixel7": (
                "Mozilla/5.0 (Linux; Android 14; Pixel 7) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/124.0 Mobile Safari/537.36"
            ),
        }

        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=headless)
            ctx_kwargs: dict[str, Any] = {"viewport": viewport_map.get(viewport, viewport_map["desktop"])}
            ua = ua_map.get(viewport)
            if ua:
                ctx_kwargs["user_agent"] = ua
            ctx_kwargs["base_url"] = self.base_url
            context = await browser.new_context(**ctx_kwargs)

            if user_credentials:
                # Pre-auth: hit /api/auth/login from a temp request context and
                # transplant the cookies onto the browser context.
                login = self._client.post(
                    "/api/auth/login",
                    json={
                        "email": user_credentials["email"],
                        "password": user_credentials["password"],
                    },
                    headers={"X-CSRF-Token": "_dummy_"},
                )
                # Note: CSRF check applies — fall back to creating a session first
                if login.status_code in (401, 403):
                    me = self._client.get("/api/auth/me")
                    csrf = me.json().get("csrf_token")
                    cookies = me.cookies
                    login = self._client.post(
                        "/api/auth/login",
                        json={
                            "email": user_credentials["email"],
                            "password": user_credentials["password"],
                        },
                        headers={"X-CSRF-Token": csrf or "_dummy_"},
                        cookies=cookies,
                    )
                if login.status_code != 200:
                    raise RuntimeError(f"pre-auth failed: {login.status_code} {login.text}")

                cookies_payload = []
                for cookie in login.cookies.jar:
                    cookies_payload.append(
                        {
                            "name": cookie.name,
                            "value": cookie.value,
                            "domain": "localhost",
                            "path": "/",
                        }
                    )
                if cookies_payload:
                    await context.add_cookies(cookies_payload)

            try:
                yield context
            finally:
                await context.close()
                await browser.close()

    def close(self) -> None:
        self._client.close()
