# SPDX-License-Identifier: Apache-2.0
"""Runtime configuration for the shop_v1 backend."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="",
        env_file=None,
        case_sensitive=False,
    )

    database_url: str = "sqlite:////tmp/shop_v1.sqlite"
    default_seed: int = 42
    test_mode: bool = False
    log_level: str = "info"
    static_dir: str = "/app/static"
    cors_origins: list[str] = ["http://localhost:5173"]
    session_cookie_name: str = "shop_v1_session"
    csrf_cookie_name: str = "shop_v1_csrf"
    default_session_ttl_s: int = 60 * 60 * 24 * 7  # 7 days

    @property
    def database_path(self) -> Path:
        prefix = "sqlite:///"
        if self.database_url.startswith(prefix):
            return Path(self.database_url[len(prefix):])
        raise ValueError(f"Unsupported database url: {self.database_url}")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    import os

    return Settings(
        database_url=os.environ.get("DATABASE_URL", "sqlite:////tmp/shop_v1.sqlite"),
        default_seed=int(os.environ.get("DEFAULT_SEED", "42")),
        test_mode=os.environ.get("REVAR_TEST_MODE", "0") in ("1", "true", "True"),
        log_level=os.environ.get("LOG_LEVEL", "info"),
        static_dir=os.environ.get("STATIC_DIR", "/app/static"),
    )
