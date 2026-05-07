# SPDX-License-Identifier: Apache-2.0
"""SDK-facing admin endpoints, gated by REVAR_TEST_MODE.

These let the SDK reset state, configure modifiers, freeze time, and read
backend rows for success_fn predicates. They are refused at startup if test
mode is not enabled (see main.py).
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from resurf_models.shop_v1 import seed_database
from sqlalchemy import text

from ..config import get_settings
from ..deps import get_engine, reset_engine
from ..modifiers import get_config

router = APIRouter()


class ResetPayload(BaseModel):
    seed: int | None = None


@router.post("/__test__/reset")
def reset(payload: ResetPayload | None = None) -> dict:
    settings = get_settings()
    seed = (payload.seed if payload else None) or settings.default_seed

    # Drop pooled connections, re-seed, reset modifier config.
    reset_engine()
    seed_database(settings.database_url, seed=seed)
    get_config().reset()
    return {"ok": True, "seed": seed}


class ConfigurePayload(BaseModel):
    latency_profile: str | None = None
    payment_outcome: Any = None
    server_error_rate: float | None = None
    server_error_paths: list[str] | None = None
    session_ttl_s: int | None = None
    frozen_time_iso: str | None = None


@router.post("/__test__/configure")
def configure(payload: ConfigurePayload) -> dict:
    cfg = get_config()
    cfg.update({k: v for k, v in payload.model_dump().items() if v is not None})
    return {"ok": True, "modifiers": cfg.to_dict()}


@router.get("/__test__/state")
def state(table: str | None = None) -> dict:
    """Generic state reader for success_fn predicates.

    Without `table`, returns a digest of well-known counters. With `table`,
    returns rows of that table (limited). For complex queries the SDK reads
    SQLite directly via StateReader, bypassing this endpoint entirely.
    """
    settings = get_settings()
    engine = get_engine()
    with engine.connect() as conn:
        if table is None:
            counts = {}
            for tbl in [
                "user",
                "product",
                "category",
                "coupon",
                "cart",
                "cartitem",
                "order",
                "orderitem",
                "paymentattempt",
                "session",
                "address",
                "return",
                "eventlog",
            ]:
                try:
                    n = conn.execute(text(f'SELECT COUNT(*) FROM "{tbl}"')).scalar()
                    counts[tbl] = int(n or 0)
                except Exception:
                    counts[tbl] = -1
            return {
                "modifiers": get_config().to_dict(),
                "counts": counts,
                "database_url": settings.database_url,
            }
        # Whitelist tables for safety
        allowed = {
            "user",
            "product",
            "category",
            "coupon",
            "cart",
            "cartitem",
            "order",
            "orderitem",
            "paymentattempt",
            "session",
            "address",
            "return",
            "eventlog",
        }
        if table not in allowed:
            raise HTTPException(status_code=400, detail="unknown_table")
        result = conn.execute(text(f'SELECT * FROM "{table}" LIMIT 200'))
        return {"table": table, "rows": [dict(r._mapping) for r in result]}


class FreezeTimePayload(BaseModel):
    iso: str | None = None


@router.post("/__test__/freeze_time")
def freeze_time(payload: FreezeTimePayload) -> dict:
    cfg = get_config()
    cfg.update({"frozen_time_iso": payload.iso})
    return {"ok": True, "frozen_time_iso": cfg.frozen_time_iso}


class QueryPayload(BaseModel):
    sql: str
    params: dict[str, Any] = {}


@router.post("/__test__/query")
def query(payload: QueryPayload) -> dict:
    """Run a read-only SQL query. Whitelisted to SELECT statements.

    The SDK uses this for success_fn predicates so it doesn't need a bind
    mount of the SQLite file.
    """
    sql = payload.sql.strip().rstrip(";")
    lowered = sql.lower().lstrip("(")
    if not lowered.startswith(("select", "with")):
        raise HTTPException(status_code=400, detail="only SELECT/WITH queries allowed")
    # Simple multi-statement guard
    if ";" in sql:
        raise HTTPException(status_code=400, detail="only single statements allowed")

    engine = get_engine()
    with engine.connect() as conn:
        try:
            result = conn.execute(text(sql), payload.params or {})
            rows = list(result)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"query_error: {exc}") from exc
        return {
            "rows": [dict(r._mapping) if hasattr(r, "_mapping") else {"value": r} for r in rows],
            "count": len(rows),
        }
