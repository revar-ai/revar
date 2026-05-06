# SPDX-License-Identifier: Apache-2.0
"""Randomly inject 5xx errors on configured paths to test agent retry behavior."""

from __future__ import annotations

import random

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from ..modifiers import get_config


class ServerErrorRateMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        cfg = get_config()
        if cfg.server_error_rate > 0 and request.method == "GET":
            path = request.url.path
            for prefix in cfg.server_error_paths:
                if path.startswith(prefix) and not path.startswith("/__test__"):
                    if random.random() < cfg.server_error_rate:
                        return JSONResponse(
                            {"error": "internal_server_error", "transient": True},
                            status_code=503,
                        )
                    break
        return await call_next(request)
