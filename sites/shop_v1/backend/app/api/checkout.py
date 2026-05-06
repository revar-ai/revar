# SPDX-License-Identifier: Apache-2.0
"""Multi-step checkout: shipping, coupon (this one applies!), review, confirm.

Confirm is where PaymentOutcome plays. The modifier config drives the outcome
of the simulated charge; it can be a single value or a sequence (consumed in
order, last value sticks) to model "first attempt declined, second succeeds".
"""

from __future__ import annotations

import asyncio
from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from revar_models.shop_v1.models import (
    Address,
    Cart,
    CartItem,
    Coupon,
    Order,
    OrderItem,
    PaymentAttempt,
    Product,
)
from sqlmodel import select

from ..deps import CSRF, DB, CurrentUser, SessionDep
from ..modifiers import get_config

router = APIRouter()


def _draft_order_for_session(db, session_token: str) -> Order | None:
    return db.exec(
        select(Order)
        .where(Order.status == "draft")
        .order_by(Order.created_at.desc())  # type: ignore[attr-defined]
    ).first()


def _serialize_cart_for_review(db, cart: Cart) -> dict:
    items = db.exec(select(CartItem).where(CartItem.cart_id == cart.id)).all()
    out = []
    subtotal = 0
    for it in items:
        p = db.get(Product, it.product_id)
        if p is None:
            continue
        line = it.quantity * p.price_cents
        subtotal += line
        out.append(
            {
                "product_id": p.id,
                "name": p.name,
                "unit_price_cents": p.price_cents,
                "quantity": it.quantity,
                "line_total_cents": line,
                "in_stock": p.stock >= it.quantity,
            }
        )
    return {"items": out, "subtotal_cents": subtotal}


def _apply_coupon(db, code: str, subtotal_cents: int) -> tuple[Coupon | None, int]:
    coupon = db.exec(select(Coupon).where(Coupon.code == code.upper())).first()
    if coupon is None or not coupon.active:
        return None, 0
    if coupon.expires_at and coupon.expires_at < datetime.utcnow():
        return None, 0
    if subtotal_cents < coupon.min_subtotal_cents:
        return None, 0
    discount = 0
    if coupon.percent_off:
        discount += subtotal_cents * coupon.percent_off // 100
    if coupon.flat_off_cents:
        discount += coupon.flat_off_cents
    return coupon, min(discount, subtotal_cents)


@router.post("/api/checkout/start", dependencies=[CSRF])
def checkout_start(user: CurrentUser, s: SessionDep, db: DB) -> dict:
    cart = db.exec(select(Cart).where(Cart.session_token == s.token)).first()
    if cart is None:
        raise HTTPException(status_code=400, detail="empty_cart")
    items = db.exec(select(CartItem).where(CartItem.cart_id == cart.id)).all()
    if not items:
        raise HTTPException(status_code=400, detail="empty_cart")

    default_addr = db.exec(
        select(Address).where(Address.user_id == user.id, Address.is_default == True)  # noqa: E712
    ).first()
    if default_addr is None:
        default_addr = db.exec(select(Address).where(Address.user_id == user.id)).first()

    subtotal = sum(
        (db.get(Product, it.product_id).price_cents * it.quantity)  # type: ignore[union-attr]
        for it in items
    )
    order = Order(
        user_id=user.id,
        shipping_address_id=default_addr.id if default_addr else 0,
        subtotal_cents=subtotal,
        total_cents=subtotal,
        status="draft",
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    return {"order_id": order.id, "subtotal_cents": subtotal}


class ShippingPayload(BaseModel):
    address_id: int


@router.patch("/api/checkout/shipping", dependencies=[CSRF])
def checkout_shipping(payload: ShippingPayload, user: CurrentUser, db: DB) -> dict:
    order = db.exec(
        select(Order).where(Order.user_id == user.id, Order.status == "draft")
    ).first()
    if order is None:
        raise HTTPException(status_code=400, detail="no_draft_order")
    addr = db.get(Address, payload.address_id)
    if addr is None or addr.user_id != user.id:
        raise HTTPException(status_code=404, detail="address_not_found")
    order.shipping_address_id = addr.id  # type: ignore[assignment]
    db.add(order)
    db.commit()
    return {"ok": True, "order_id": order.id, "shipping_address_id": addr.id}


class CheckoutCouponPayload(BaseModel):
    code: str = Field(min_length=1, max_length=64)


@router.post("/api/checkout/coupon", dependencies=[CSRF])
def checkout_coupon(payload: CheckoutCouponPayload, user: CurrentUser, db: DB) -> dict:
    """The *real* coupon application point. Cart-side input is decorative."""
    order = db.exec(
        select(Order).where(Order.user_id == user.id, Order.status == "draft")
    ).first()
    if order is None:
        raise HTTPException(status_code=400, detail="no_draft_order")
    coupon, discount = _apply_coupon(db, payload.code, order.subtotal_cents)
    if coupon is None:
        raise HTTPException(status_code=400, detail="coupon_invalid_or_expired")
    order.coupon_code = coupon.code
    order.discount_cents = discount
    order.total_cents = max(0, order.subtotal_cents - discount)
    db.add(order)
    db.commit()
    return {
        "ok": True,
        "applied_at_checkout": True,
        "coupon": coupon.code,
        "discount_cents": discount,
        "total_cents": order.total_cents,
    }


@router.delete("/api/checkout/coupon", dependencies=[CSRF])
def remove_checkout_coupon(user: CurrentUser, db: DB) -> dict:
    order = db.exec(
        select(Order).where(Order.user_id == user.id, Order.status == "draft")
    ).first()
    if order is None:
        raise HTTPException(status_code=400, detail="no_draft_order")
    order.coupon_code = None
    order.discount_cents = 0
    order.total_cents = order.subtotal_cents
    db.add(order)
    db.commit()
    return {"ok": True, "total_cents": order.total_cents}


@router.get("/api/checkout/review")
def checkout_review(user: CurrentUser, s: SessionDep, db: DB) -> dict:
    order = db.exec(
        select(Order).where(Order.user_id == user.id, Order.status == "draft")
    ).first()
    if order is None:
        raise HTTPException(status_code=400, detail="no_draft_order")
    cart = db.exec(select(Cart).where(Cart.session_token == s.token)).first()
    if cart is None:
        raise HTTPException(status_code=400, detail="empty_cart")
    cart_payload = _serialize_cart_for_review(db, cart)

    # Re-validate stock at review time (so out-of-stock issues surface here)
    out_of_stock = [it for it in cart_payload["items"] if not it["in_stock"]]
    address = db.get(Address, order.shipping_address_id)

    return {
        "order_id": order.id,
        "items": cart_payload["items"],
        "subtotal_cents": order.subtotal_cents,
        "discount_cents": order.discount_cents,
        "total_cents": order.total_cents,
        "coupon_code": order.coupon_code,
        "shipping_address": (
            {
                "id": address.id,
                "full_name": address.full_name,
                "line1": address.line1,
                "line2": address.line2,
                "city": address.city,
                "state": address.state,
                "postal_code": address.postal_code,
                "country": address.country,
            }
            if address
            else None
        ),
        "out_of_stock_items": out_of_stock,
    }


class ConfirmPayload(BaseModel):
    card_number: str = Field(min_length=12, max_length=24)
    card_exp: str
    card_cvc: str = Field(min_length=3, max_length=4)


@router.post("/api/checkout/confirm", dependencies=[CSRF])
async def checkout_confirm(
    payload: ConfirmPayload, user: CurrentUser, s: SessionDep, db: DB
) -> dict:
    order = db.exec(
        select(Order).where(Order.user_id == user.id, Order.status == "draft")
    ).first()
    if order is None:
        raise HTTPException(status_code=400, detail="no_draft_order")

    # Materialize cart into order items (idempotent on the draft order)
    cart = db.exec(select(Cart).where(Cart.session_token == s.token)).first()
    if cart is None:
        raise HTTPException(status_code=400, detail="empty_cart")
    cart_items = db.exec(select(CartItem).where(CartItem.cart_id == cart.id)).all()
    if not cart_items:
        raise HTTPException(status_code=400, detail="empty_cart")

    # Re-validate stock atomically right before payment
    for it in cart_items:
        p = db.get(Product, it.product_id)
        if p is None or p.stock < it.quantity:
            raise HTTPException(
                status_code=409,
                detail={
                    "error": "out_of_stock",
                    "product_id": it.product_id,
                    "product_name": p.name if p else "unknown",
                    "requested": it.quantity,
                    "available": p.stock if p else 0,
                },
            )

    # Drop existing draft order items (in case of retry) and re-add
    existing_items = db.exec(select(OrderItem).where(OrderItem.order_id == order.id)).all()
    for ei in existing_items:
        db.delete(ei)
    db.flush()
    for it in cart_items:
        p = db.get(Product, it.product_id)
        db.add(
            OrderItem(
                order_id=order.id,
                product_id=p.id,  # type: ignore[arg-type, union-attr]
                product_name=p.name,  # type: ignore[union-attr]
                unit_price_cents=p.price_cents,  # type: ignore[union-attr]
                quantity=it.quantity,
            )
        )

    cfg = get_config()
    outcome = cfg.next_payment_outcome()

    last4 = payload.card_number[-4:]
    order.payment_attempts += 1

    if outcome == "timeout":
        # Sleep a long time then return 504 (the agent's HTTP client may give up first)
        await asyncio.sleep(30)
        order.last_payment_error = "gateway_timeout"
        db.add(PaymentAttempt(order_id=order.id, card_last4=last4, outcome="timeout"))
        db.add(order)
        db.commit()
        raise HTTPException(status_code=504, detail="gateway_timeout")

    if outcome == "3ds_required":
        db.add(
            PaymentAttempt(
                order_id=order.id,
                card_last4=last4,
                outcome="3ds_required",
                error_code="3DS_REDIRECT",
            )
        )
        order.last_payment_error = "3ds_required"
        db.add(order)
        db.commit()
        return {
            "status": "3ds_required",
            "redirect_url": f"/checkout/3ds?order_id={order.id}",
        }

    if outcome == "declined":
        order.status = "draft"  # stays as draft so retries are possible
        order.last_payment_error = "card_declined"
        db.add(
            PaymentAttempt(
                order_id=order.id,
                card_last4=last4,
                outcome="declined",
                error_code="INSUFFICIENT_FUNDS",
            )
        )
        db.add(order)
        # Mark a stub failed Order as well so success_fns can detect "actually retried"
        # without having to query payment_attempts directly.
        db.commit()
        raise HTTPException(
            status_code=402,
            detail={"error": "card_declined", "code": "INSUFFICIENT_FUNDS"},
        )

    # success
    for it in cart_items:
        p = db.get(Product, it.product_id)
        if p is not None:
            p.stock = max(0, p.stock - it.quantity)
            db.add(p)
    order.status = "paid"
    order.paid_at = datetime.utcnow()
    order.last_payment_error = None
    db.add(order)
    db.add(PaymentAttempt(order_id=order.id, card_last4=last4, outcome="success"))

    # Empty the cart on successful checkout
    for it in cart_items:
        db.delete(it)
    cart.coupon_code = None
    cart.cart_coupon_attempt = None
    db.add(cart)

    db.commit()
    db.refresh(order)
    return {
        "status": "paid",
        "order_id": order.id,
        "total_cents": order.total_cents,
        "paid_at": order.paid_at.isoformat() if order.paid_at else None,
    }
