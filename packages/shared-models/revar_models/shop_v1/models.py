# SPDX-License-Identifier: Apache-2.0
"""SQLModel schema for shop_v1.

This module is the single source of truth for shop_v1's data shape. The site
backend writes to it; the revar SDK reads from it for success_fn
predicates. Keep field semantics stable across versions where possible.
"""

from __future__ import annotations

from datetime import datetime

from sqlmodel import Field, SQLModel


# ---------------------------------------------------------------------------
# Catalog
# ---------------------------------------------------------------------------


class Category(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    slug: str = Field(unique=True, index=True)
    name: str
    description: str = ""


class Product(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    slug: str = Field(unique=True, index=True)
    name: str = Field(index=True)
    description: str
    short_description: str
    price_cents: int
    currency: str = "USD"
    stock: int = 0
    image_url: str
    category_id: int = Field(foreign_key="category.id", index=True)
    rating: float = 0.0
    rating_count: int = 0
    tags: str = ""  # comma-separated for cheap filtering


# ---------------------------------------------------------------------------
# Users / sessions
# ---------------------------------------------------------------------------


class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True)
    password_hash: str
    full_name: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Address(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    label: str = "home"
    full_name: str
    line1: str
    line2: str = ""
    city: str
    state: str
    postal_code: str
    country: str = "US"
    is_default: bool = False


class Session(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    token: str = Field(unique=True, index=True)
    user_id: int | None = Field(default=None, foreign_key="user.id", index=True)
    csrf_token: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime


# ---------------------------------------------------------------------------
# Cart
# ---------------------------------------------------------------------------


class Cart(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    session_token: str = Field(unique=True, index=True)
    user_id: int | None = Field(default=None, foreign_key="user.id", index=True)
    coupon_code: str | None = None
    cart_coupon_attempt: str | None = None  # last code typed in *cart-side* input (does not apply)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class CartItem(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    cart_id: int = Field(foreign_key="cart.id", index=True)
    product_id: int = Field(foreign_key="product.id", index=True)
    quantity: int


# ---------------------------------------------------------------------------
# Coupons
# ---------------------------------------------------------------------------


class Coupon(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    code: str = Field(unique=True, index=True)
    description: str
    percent_off: int = 0  # 0-100
    flat_off_cents: int = 0
    min_subtotal_cents: int = 0
    expires_at: datetime | None = None
    active: bool = True


# ---------------------------------------------------------------------------
# Orders
# ---------------------------------------------------------------------------


class Order(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    shipping_address_id: int = Field(foreign_key="address.id")
    coupon_code: str | None = None
    subtotal_cents: int
    discount_cents: int = 0
    tax_cents: int = 0
    shipping_cents: int = 0
    total_cents: int
    status: str = "pending"  # pending | paid | failed | cancelled | refunded
    payment_attempts: int = 0
    last_payment_error: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    paid_at: datetime | None = None


class OrderItem(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    order_id: int = Field(foreign_key="order.id", index=True)
    product_id: int = Field(foreign_key="product.id")
    product_name: str  # snapshot
    unit_price_cents: int
    quantity: int


class PaymentAttempt(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    order_id: int = Field(foreign_key="order.id", index=True)
    card_last4: str
    outcome: str  # success | declined | timeout | 3ds_required
    error_code: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Return(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    order_id: int = Field(foreign_key="order.id", index=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    reason: str
    status: str = "requested"  # requested | approved | rejected | refunded
    created_at: datetime = Field(default_factory=datetime.utcnow)


class EventLog(SQLModel, table=True):
    """Generic append-only event log so navigation/interaction tasks can be SQL-checkable.

    Examples:
        type='product_view', detail='{"slug": "acme-bluetooth-speaker"}'
        type='search', detail='{"q": "speaker"}'
        type='cart_open', detail='{"path": "/cart"}'
    """

    id: int | None = Field(default=None, primary_key=True)
    session_token: str | None = Field(default=None, index=True)
    user_id: int | None = Field(default=None, foreign_key="user.id", index=True)
    type: str = Field(index=True)
    detail: str = ""  # JSON-encoded
    created_at: datetime = Field(default_factory=datetime.utcnow)
