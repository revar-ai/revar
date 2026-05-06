# SPDX-License-Identifier: Apache-2.0
"""Inject configurable per-route latency to mimic real-world network conditions."""

from __future__ import annotations

import asyncio
import random

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from ..modifiers import get_config, latency_for_path


class LatencyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if path.startswith("/api/") and not path.startswith("/__test__"):
            cfg = get_config()
            lo, hi = latency_for_path(cfg.latency_profile, path)
            if hi > 0:
                await asyncio.sleep(random.uniform(lo, hi))
        return await call_next(request)
