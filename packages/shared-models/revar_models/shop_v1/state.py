# SPDX-License-Identifier: Apache-2.0
"""State reader for shop_v1 success_fn predicates.

The revar SDK uses StateReader to evaluate task success against the
backend SQLite file directly, bypassing the HTTP layer. This is what makes
deterministic eval possible: no flaky DOM scraping for "did the order go
through?", just a SQL query against shared models.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlmodel import Session as DBSession
from sqlmodel import create_engine, select

from .models import (
    Address,
    Cart,
    CartItem,
    Coupon,
    Order,
    OrderItem,
    PaymentAttempt,
    Product,
    Return,
    User,
)
from .seed import seeded_user_id


class StateReader:
    """Read-only view of the shop_v1 database for success predicates."""

    def __init__(self, database_url: str) -> None:
        self.database_url = database_url
        self._engine = create_engine(database_url)

    # ------------------------------------------------------------------
    # Generic helpers used by YAML state_predicate tasks
    # ------------------------------------------------------------------

    def query_scalar(self, sql: str, **bindings: Any) -> Any:
        """Run a raw SQL query and return the first column of the first row."""
        with self._engine.connect() as conn:
            row = conn.execute(text(sql), bindings).first()
            if row is None:
                return None
            return row[0]

    def query_rows(self, sql: str, **bindings: Any) -> list[dict[str, Any]]:
        """Run a raw SQL query and return all rows as dicts."""
        with self._engine.connect() as conn:
            result = conn.execute(text(sql), bindings)
            return [dict(row._mapping) for row in result]

    def default_bindings(self) -> dict[str, Any]:
        """Useful named parameters that tasks can reference (e.g. :seeded_user_id)."""
        return {"seeded_user_id": seeded_user_id(self.database_url)}

    # ------------------------------------------------------------------
    # Typed accessors used by Python escape-hatch success_fn implementations
    # ------------------------------------------------------------------

    def orders_for_seeded_user(self, status: str | None = None) -> list[Order]:
        with DBSession(self._engine) as db:
            stmt = select(Order).where(Order.user_id == seeded_user_id(self.database_url))
            if status is not None:
                stmt = stmt.where(Order.status == status)
            return list(db.exec(stmt).all())

    def latest_order_for_seeded_user(self) -> Order | None:
        with DBSession(self._engine) as db:
            stmt = (
                select(Order)
                .where(Order.user_id == seeded_user_id(self.database_url))
                .order_by(Order.created_at.desc())  # type: ignore[attr-defined]
            )
            return db.exec(stmt).first()

    def order_items(self, order_id: int) -> list[OrderItem]:
        with DBSession(self._engine) as db:
            return list(db.exec(select(OrderItem).where(OrderItem.order_id == order_id)).all())

    def payment_attempts(self, order_id: int) -> list[PaymentAttempt]:
        with DBSession(self._engine) as db:
            return list(
                db.exec(select(PaymentAttempt).where(PaymentAttempt.order_id == order_id)).all()
            )

    def product_by_name(self, name: str) -> Product | None:
        with DBSession(self._engine) as db:
            return db.exec(select(Product).where(Product.name == name)).first()

    def product_by_slug(self, slug: str) -> Product | None:
        with DBSession(self._engine) as db:
            return db.exec(select(Product).where(Product.slug == slug)).first()

    def coupon(self, code: str) -> Coupon | None:
        with DBSession(self._engine) as db:
            return db.exec(select(Coupon).where(Coupon.code == code)).first()

    def cart_for_session(self, session_token: str) -> Cart | None:
        with DBSession(self._engine) as db:
            return db.exec(select(Cart).where(Cart.session_token == session_token)).first()

    def cart_items(self, cart_id: int) -> list[CartItem]:
        with DBSession(self._engine) as db:
            return list(db.exec(select(CartItem).where(CartItem.cart_id == cart_id)).all())

    def returns_for_seeded_user(self) -> list[Return]:
        with DBSession(self._engine) as db:
            return list(
                db.exec(
                    select(Return).where(Return.user_id == seeded_user_id(self.database_url))
                ).all()
            )

    def addresses_for_seeded_user(self) -> list[Address]:
        with DBSession(self._engine) as db:
            return list(
                db.exec(
                    select(Address).where(Address.user_id == seeded_user_id(self.database_url))
                ).all()
            )

    def all_users(self) -> list[User]:
        with DBSession(self._engine) as db:
            return list(db.exec(select(User)).all())


__all__ = ["StateReader"]
