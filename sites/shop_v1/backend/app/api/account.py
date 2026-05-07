# SPDX-License-Identifier: Apache-2.0
"""Account endpoints: orders list (paginated), order detail, addresses, returns."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from resurf_models.shop_v1.models import Address, Order, OrderItem, Return
from sqlmodel import func, select

from ..deps import CSRF, DB, CurrentUser

router = APIRouter()


@router.get("/api/account/orders")
def list_orders(user: CurrentUser, db: DB, page: int = 1, per_page: int = 10) -> dict:
    if page < 1:
        page = 1
    if per_page < 1 or per_page > 50:
        per_page = 10
    base = select(Order).where(Order.user_id == user.id, Order.status != "draft")
    total = db.exec(select(func.count()).select_from(base.subquery())).one()
    if isinstance(total, tuple):
        total = total[0]
    rows = db.exec(
        base.order_by(Order.created_at.desc())  # type: ignore[attr-defined]
        .offset((page - 1) * per_page)
        .limit(per_page)
    ).all()
    return {
        "items": [
            {
                "id": o.id,
                "status": o.status,
                "total_cents": o.total_cents,
                "created_at": o.created_at.isoformat() if o.created_at else None,
            }
            for o in rows
        ],
        "page": page,
        "per_page": per_page,
        "total": int(total),
        "total_pages": max(1, (int(total) + per_page - 1) // per_page),
    }


@router.get("/api/account/orders/{order_id}")
def order_detail(order_id: int, user: CurrentUser, db: DB) -> dict:
    o = db.get(Order, order_id)
    if o is None or o.user_id != user.id:
        raise HTTPException(status_code=404, detail="order_not_found")
    items = db.exec(select(OrderItem).where(OrderItem.order_id == o.id)).all()
    return {
        "id": o.id,
        "status": o.status,
        "subtotal_cents": o.subtotal_cents,
        "discount_cents": o.discount_cents,
        "total_cents": o.total_cents,
        "coupon_code": o.coupon_code,
        "payment_attempts": o.payment_attempts,
        "last_payment_error": o.last_payment_error,
        "created_at": o.created_at.isoformat() if o.created_at else None,
        "paid_at": o.paid_at.isoformat() if o.paid_at else None,
        "items": [
            {
                "product_id": it.product_id,
                "product_name": it.product_name,
                "unit_price_cents": it.unit_price_cents,
                "quantity": it.quantity,
            }
            for it in items
        ],
    }


class ReturnPayload(BaseModel):
    reason: str = Field(min_length=3, max_length=500)


@router.post("/api/account/orders/{order_id}/return", dependencies=[CSRF])
def request_return(order_id: int, payload: ReturnPayload, user: CurrentUser, db: DB) -> dict:
    o = db.get(Order, order_id)
    if o is None or o.user_id != user.id:
        raise HTTPException(status_code=404, detail="order_not_found")
    if o.status != "paid":
        raise HTTPException(status_code=400, detail="order_not_returnable")
    r = Return(order_id=o.id, user_id=user.id, reason=payload.reason)  # type: ignore[arg-type]
    db.add(r)
    db.commit()
    db.refresh(r)
    return {"id": r.id, "status": r.status, "order_id": o.id}


@router.get("/api/account/addresses")
def list_addresses(user: CurrentUser, db: DB) -> list[dict]:
    rows = db.exec(select(Address).where(Address.user_id == user.id)).all()
    return [
        {
            "id": a.id,
            "label": a.label,
            "full_name": a.full_name,
            "line1": a.line1,
            "line2": a.line2,
            "city": a.city,
            "state": a.state,
            "postal_code": a.postal_code,
            "country": a.country,
            "is_default": a.is_default,
        }
        for a in rows
    ]


class AddressPayload(BaseModel):
    label: str = "home"
    full_name: str
    line1: str
    line2: str = ""
    city: str
    state: str
    postal_code: str
    country: str = "US"
    is_default: bool = False


@router.post("/api/account/addresses", dependencies=[CSRF])
def create_address(payload: AddressPayload, user: CurrentUser, db: DB) -> dict:
    if payload.is_default:
        existing = db.exec(
            select(Address).where(Address.user_id == user.id, Address.is_default == True)  # noqa: E712
        ).all()
        for a in existing:
            a.is_default = False
            db.add(a)
    addr = Address(user_id=user.id, **payload.model_dump())  # type: ignore[arg-type]
    db.add(addr)
    db.commit()
    db.refresh(addr)
    return {"id": addr.id, "label": addr.label, "is_default": addr.is_default}
