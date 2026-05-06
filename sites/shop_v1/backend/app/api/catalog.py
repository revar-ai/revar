# SPDX-License-Identifier: Apache-2.0
"""Catalog endpoints: categories, paginated list, search (cursor for infinite scroll), detail."""

from __future__ import annotations

import base64
import json

from revar_models.shop_v1.models import Category, EventLog, Product
from fastapi import APIRouter, HTTPException, Query, Request
from sqlmodel import func, or_, select

from ..config import get_settings
from ..deps import DB

router = APIRouter()


def _log_event(db, request: Request, type_: str, detail: dict) -> None:
    settings = get_settings()
    token = request.cookies.get(settings.session_cookie_name)
    db.add(EventLog(session_token=token, type=type_, detail=json.dumps(detail)))
    db.commit()


@router.get("/api/categories")
def list_categories(db: DB) -> list[dict]:
    rows = db.exec(select(Category).order_by(Category.name)).all()
    return [{"slug": c.slug, "name": c.name, "description": c.description} for c in rows]


def _serialize_product(p: Product) -> dict:
    return {
        "id": p.id,
        "slug": p.slug,
        "name": p.name,
        "short_description": p.short_description,
        "price_cents": p.price_cents,
        "currency": p.currency,
        "stock": p.stock,
        "image_url": p.image_url,
        "category_id": p.category_id,
        "rating": p.rating,
        "rating_count": p.rating_count,
        "tags": [t for t in p.tags.split(",") if t],
    }


@router.get("/api/products")
def list_products(
    db: DB,
    category: str | None = None,
    q: str | None = None,
    min_price: int | None = None,
    max_price: int | None = None,
    in_stock: bool | None = None,
    sort: str = "name",
    page: int = 1,
    per_page: int = 12,
) -> dict:
    """Paginated product list (URL-synced, ?page=N).

    Used by the main catalog page; pagination here is the production-shape
    surface (vs infinite scroll on /search).
    """
    if page < 1:
        page = 1
    if per_page < 1 or per_page > 60:
        per_page = 12

    stmt = select(Product)
    if category:
        cat = db.exec(select(Category).where(Category.slug == category)).first()
        if cat is None:
            raise HTTPException(status_code=404, detail="unknown_category")
        stmt = stmt.where(Product.category_id == cat.id)
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(or_(Product.name.ilike(like), Product.tags.ilike(like)))  # type: ignore[attr-defined]
    if min_price is not None:
        stmt = stmt.where(Product.price_cents >= min_price)
    if max_price is not None:
        stmt = stmt.where(Product.price_cents <= max_price)
    if in_stock is True:
        stmt = stmt.where(Product.stock > 0)

    sort_map = {
        "name": Product.name.asc(),  # type: ignore[attr-defined]
        "price_asc": Product.price_cents.asc(),  # type: ignore[attr-defined]
        "price_desc": Product.price_cents.desc(),  # type: ignore[attr-defined]
        "rating": Product.rating.desc(),  # type: ignore[attr-defined]
    }
    stmt = stmt.order_by(sort_map.get(sort, sort_map["name"]))

    # Total count via separate query (cheap on SQLite for our sizes)
    total = db.exec(select(func.count()).select_from(stmt.subquery())).one()
    if isinstance(total, tuple):
        total = total[0]

    items = db.exec(stmt.offset((page - 1) * per_page).limit(per_page)).all()
    return {
        "items": [_serialize_product(p) for p in items],
        "page": page,
        "per_page": per_page,
        "total": int(total),
        "total_pages": max(1, (int(total) + per_page - 1) // per_page),
    }


def _encode_cursor(idx: int) -> str:
    return base64.urlsafe_b64encode(json.dumps({"i": idx}).encode()).decode().rstrip("=")


def _decode_cursor(cursor: str) -> int:
    pad = "=" * (-len(cursor) % 4)
    try:
        data = json.loads(base64.urlsafe_b64decode(cursor + pad))
        return int(data.get("i", 0))
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail="invalid_cursor") from exc


@router.get("/api/products/search")
def search_products(
    request: Request,
    db: DB,
    q: str = Query(default="", min_length=0, max_length=200),
    cursor: str | None = None,
    limit: int = 12,
) -> dict:
    """Cursor-paginated search results for infinite scroll.

    Different shape from /api/products so the frontend can use IntersectionObserver
    pagination on this route while keeping URL-synced pagination on the main list.
    """
    if limit < 1 or limit > 30:
        limit = 12
    offset = _decode_cursor(cursor) if cursor else 0

    stmt = select(Product).order_by(Product.id)
    if q.strip():
        like = f"%{q.strip()}%"
        stmt = stmt.where(or_(Product.name.ilike(like), Product.tags.ilike(like)))  # type: ignore[attr-defined]

    items = db.exec(stmt.offset(offset).limit(limit + 1)).all()
    has_more = len(items) > limit
    items = items[:limit]
    next_cursor = _encode_cursor(offset + limit) if has_more else None
    if q.strip() and offset == 0:
        _log_event(db, request, "search", {"q": q.strip()})
    return {
        "items": [_serialize_product(p) for p in items],
        "next_cursor": next_cursor,
        "has_more": has_more,
    }


@router.get("/api/products/{slug}")
def product_detail(slug: str, request: Request, db: DB) -> dict:
    p = db.exec(select(Product).where(Product.slug == slug)).first()
    if p is None:
        raise HTTPException(status_code=404, detail="product_not_found")
    out = _serialize_product(p)
    cat = db.get(Category, p.category_id)
    out["category"] = {"slug": cat.slug, "name": cat.name} if cat else None
    out["description"] = p.description
    _log_event(db, request, "product_view", {"slug": slug, "id": p.id})
    return out
