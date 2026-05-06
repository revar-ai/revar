# SPDX-License-Identifier: Apache-2.0
"""Cart endpoints.

Notable: the cart-side coupon input is the *ambiguous UI element*.
POST /api/cart/coupon stores `cart_coupon_attempt` and returns a 200 with
`applied_at_checkout=False`. The cart UI shows a 'Code applied' toast, but the
coupon does not actually affect totals — only POST /api/checkout/coupon does.
This is one of the deliberate adversarial-UI dimensions in shop_v1.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from revar_models.shop_v1.models import Cart, CartItem, Product
from sqlmodel import select

from ..deps import CSRF, DB, SessionDep

router = APIRouter()


def _get_or_create_cart(db, session_token: str) -> Cart:
    cart = db.exec(select(Cart).where(Cart.session_token == session_token)).first()
    if cart is None:
        cart = Cart(session_token=session_token)
        db.add(cart)
        db.commit()
        db.refresh(cart)
    return cart


def _serialize_cart(db, cart: Cart) -> dict:
    items = db.exec(select(CartItem).where(CartItem.cart_id == cart.id)).all()
    out_items = []
    subtotal = 0
    for it in items:
        p = db.get(Product, it.product_id)
        if p is None:
            continue
        line = it.quantity * p.price_cents
        subtotal += line
        out_items.append(
            {
                "id": it.id,
                "product_id": p.id,
                "slug": p.slug,
                "name": p.name,
                "image_url": p.image_url,
                "unit_price_cents": p.price_cents,
                "quantity": it.quantity,
                "line_total_cents": line,
                "in_stock": p.stock >= it.quantity,
            }
        )
    return {
        "items": out_items,
        "subtotal_cents": subtotal,
        "coupon_code": cart.coupon_code,  # actual applied (only set via checkout)
        "cart_coupon_attempt": cart.cart_coupon_attempt,  # ambiguous: code typed in cart, didn't actually apply
        "updated_at": cart.updated_at.isoformat() if cart.updated_at else None,
    }


@router.get("/api/cart")
def get_cart(s: SessionDep, db: DB) -> dict:
    cart = _get_or_create_cart(db, s.token)
    return _serialize_cart(db, cart)


class AddItemPayload(BaseModel):
    product_id: int
    quantity: int = Field(default=1, ge=1, le=99)


@router.post("/api/cart/items", dependencies=[CSRF])
def add_item(payload: AddItemPayload, s: SessionDep, db: DB) -> dict:
    cart = _get_or_create_cart(db, s.token)
    p = db.get(Product, payload.product_id)
    if p is None:
        raise HTTPException(status_code=404, detail="product_not_found")
    if p.stock <= 0:
        raise HTTPException(status_code=409, detail="out_of_stock")

    existing = db.exec(
        select(CartItem).where(CartItem.cart_id == cart.id, CartItem.product_id == p.id)
    ).first()
    if existing is None:
        db.add(CartItem(cart_id=cart.id, product_id=p.id, quantity=payload.quantity))  # type: ignore[arg-type]
    else:
        existing.quantity += payload.quantity
        db.add(existing)
    db.commit()
    db.refresh(cart)
    return _serialize_cart(db, cart)


class UpdateItemPayload(BaseModel):
    quantity: int = Field(ge=0, le=99)


@router.patch("/api/cart/items/{item_id}", dependencies=[CSRF])
def update_item(item_id: int, payload: UpdateItemPayload, s: SessionDep, db: DB) -> dict:
    cart = _get_or_create_cart(db, s.token)
    item = db.get(CartItem, item_id)
    if item is None or item.cart_id != cart.id:
        raise HTTPException(status_code=404, detail="cart_item_not_found")
    if payload.quantity == 0:
        db.delete(item)
    else:
        item.quantity = payload.quantity
        db.add(item)
    db.commit()
    db.refresh(cart)
    return _serialize_cart(db, cart)


@router.delete("/api/cart/items/{item_id}", dependencies=[CSRF])
def delete_item(item_id: int, s: SessionDep, db: DB) -> dict:
    cart = _get_or_create_cart(db, s.token)
    item = db.get(CartItem, item_id)
    if item is None or item.cart_id != cart.id:
        raise HTTPException(status_code=404, detail="cart_item_not_found")
    db.delete(item)
    db.commit()
    db.refresh(cart)
    return _serialize_cart(db, cart)


class CouponPayload(BaseModel):
    code: str = Field(min_length=1, max_length=64)


@router.post("/api/cart/coupon", dependencies=[CSRF])
def cart_coupon(payload: CouponPayload, s: SessionDep, db: DB) -> dict:
    """Cart-side coupon input — DELIBERATE AMBIGUOUS UI.

    Returns 200 with applied_at_checkout=False regardless of the code, so the
    frontend can display a "Code applied" toast that fools agents that confirm
    via UI feedback. The coupon never actually affects totals here; only
    POST /api/checkout/coupon does that.
    """
    cart = _get_or_create_cart(db, s.token)
    cart.cart_coupon_attempt = payload.code.strip().upper()
    db.add(cart)
    db.commit()
    return {
        "ok": True,
        "applied_at_checkout": False,
        "message": "Code saved. It will be applied at checkout.",
        "cart": _serialize_cart(db, cart),
    }
