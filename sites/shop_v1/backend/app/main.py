# SPDX-License-Identifier: Apache-2.0
"""shop_v1 FastAPI application entrypoint.

Serves /api/* and /__test__/* (when test mode enabled), and the React SPA
static bundle from STATIC_DIR with route-aware index.html rewriting to give
DOM-snapshot-before-hydration agents structural content.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from resurf_models.shop_v1 import seed_database

from .api import account as account_api
from .api import auth as auth_api
from .api import cart as cart_api
from .api import catalog as catalog_api
from .api import checkout as checkout_api
from .api import health as health_api
from .api import test_endpoints
from .config import get_settings
from .middleware import LatencyMiddleware, ServerErrorRateMiddleware

logger = logging.getLogger("shop_v1")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="shop_v1",
        description="A synthetic e-commerce site for resurf",
        version="0.1.0",
    )

    # ----- Middlewares -----
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(LatencyMiddleware)
    app.add_middleware(ServerErrorRateMiddleware)

    # ----- API routers -----
    app.include_router(health_api.router)
    app.include_router(catalog_api.router)
    app.include_router(cart_api.router)
    app.include_router(auth_api.router)
    app.include_router(checkout_api.router)
    app.include_router(account_api.router)

    if settings.test_mode:
        app.include_router(test_endpoints.router)
        logger.warning(
            "REVAR_TEST_MODE=1 — /__test__/* admin endpoints are exposed. "
            "Do not run with this flag in production."
        )

    # ----- Database bootstrap -----
    @app.on_event("startup")
    def _bootstrap_db() -> None:
        path = settings.database_path
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists() or os.environ.get("RESEED_ON_STARTUP", "0") in ("1", "true"):
            logger.info("Seeding database at %s with seed=%d", path, settings.default_seed)
            seed_database(settings.database_url, seed=settings.default_seed)

    # ----- Static SPA serving with route-aware index.html rewriting -----
    static_dir = Path(settings.static_dir)
    if static_dir.exists():
        # Mount /assets/* for the Vite-built JS/CSS chunks
        assets_dir = static_dir / "assets"
        if assets_dir.exists():
            app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")
        # Mount /static/* for product images and other static content
        static_assets = static_dir / "static"
        if static_assets.exists():
            app.mount("/static", StaticFiles(directory=static_assets), name="static-assets")

        index_path = static_dir / "index.html"

        def _rewrite_index(path: str) -> str:
            try:
                html = index_path.read_text()
            except FileNotFoundError:
                return "<html><body><h1>shop_v1</h1><p>Frontend not built.</p></body></html>"
            title, description = _seo_for_route(path)
            html = html.replace(
                "<title>shop_v1</title>",
                f"<title>{title}</title>",
            )
            # Inject a route-specific meta description if a placeholder is present
            html = html.replace(
                '<meta name="description" content="">',
                f'<meta name="description" content="{description}">',
            )
            return html

        @app.get("/{full_path:path}", include_in_schema=False)
        async def spa_fallback(full_path: str, request: Request) -> Response:
            # Don't intercept /api/* or /__test__/*
            if full_path.startswith("api/") or full_path.startswith("__test__"):
                return Response(status_code=404)
            # Asset paths are mounted above; if we hit here it's missing
            if full_path.startswith("assets/") or full_path.startswith("static/"):
                return Response(status_code=404)
            return HTMLResponse(_rewrite_index("/" + full_path))

    return app


def _seo_for_route(path: str) -> tuple[str, str]:
    """Return (title, meta description) for a given URL path.

    This is the lightweight SSR mitigation: even though the SPA is CSR, the
    initial HTML reflects the current route so DOM-snapshot agents see
    something structural.
    """
    p = path or "/"
    if p == "/" or p == "":
        return "Acme Shop — Home", "Audio, wearables, fragrance and more at Acme."
    if p.startswith("/products/"):
        slug = p.removeprefix("/products/").strip("/")
        if slug:
            human = slug.replace("-", " ").title()
            return f"{human} — Acme Shop", f"Buy {human} at Acme Shop."
        return "Products — Acme Shop", "Browse all products."
    if p.startswith("/products"):
        return "All Products — Acme Shop", "Browse the full catalog at Acme Shop."
    if p.startswith("/search"):
        return "Search — Acme Shop", "Search the Acme catalog."
    if p.startswith("/cart"):
        return "Cart — Acme Shop", "Review your cart."
    if p.startswith("/checkout"):
        return "Checkout — Acme Shop", "Complete your order."
    if p.startswith("/account"):
        return "My Account — Acme Shop", "Orders, addresses, and returns."
    if p.startswith("/login") or p.startswith("/signup"):
        return "Sign in — Acme Shop", "Sign in or create an account."
    return "Acme Shop", "Acme Shop"


app = create_app()
