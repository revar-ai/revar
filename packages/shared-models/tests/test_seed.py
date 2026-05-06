# SPDX-License-Identifier: Apache-2.0
"""Tests for shop_v1 seed determinism and schema."""

from __future__ import annotations

import os
import tempfile

from revar_models.shop_v1 import StateReader, seed_database
from revar_models.shop_v1.models import Coupon, Product, User
from sqlmodel import Session as DBSession
from sqlmodel import create_engine, select


def _fresh_db() -> str:
    fd, path = tempfile.mkstemp(suffix=".sqlite")
    os.close(fd)
    return f"sqlite:///{path}"


def test_seed_creates_anchor_products():
    url = _fresh_db()
    seed_database(url, seed=42)
    engine = create_engine(url)
    with DBSession(engine) as db:
        slugs = {p.slug for p in db.exec(select(Product)).all()}
    assert "acme-bluetooth-speaker" in slugs
    assert "lumen-smart-bulb" in slugs
    assert "trailmate-water-bottle" in slugs


def test_seed_is_deterministic():
    url1 = _fresh_db()
    url2 = _fresh_db()
    seed_database(url1, seed=42)
    seed_database(url2, seed=42)
    e1 = create_engine(url1)
    e2 = create_engine(url2)
    with DBSession(e1) as db1, DBSession(e2) as db2:
        prods1 = sorted(p.slug for p in db1.exec(select(Product)).all())
        prods2 = sorted(p.slug for p in db2.exec(select(Product)).all())
    assert prods1 == prods2


def test_seeded_user_exists():
    url = _fresh_db()
    seed_database(url, seed=42)
    engine = create_engine(url)
    with DBSession(engine) as db:
        u = db.exec(select(User).where(User.email == "alex@example.com")).first()
    assert u is not None
    assert u.full_name == "Alex Doe"


def test_state_reader_orders_for_user():
    url = _fresh_db()
    seed_database(url, seed=42)
    sr = StateReader(url)
    orders = sr.orders_for_seeded_user()
    # Fresh seed => no orders yet
    assert orders == []


def test_lumen_is_out_of_stock():
    url = _fresh_db()
    seed_database(url, seed=42)
    engine = create_engine(url)
    with DBSession(engine) as db:
        p = db.exec(select(Product).where(Product.slug == "lumen-smart-bulb")).first()
    assert p is not None
    assert p.stock == 0


def test_summer15_coupon_active():
    url = _fresh_db()
    seed_database(url, seed=42)
    engine = create_engine(url)
    with DBSession(engine) as db:
        c = db.exec(select(Coupon).where(Coupon.code == "SUMMER15")).first()
    assert c is not None
    assert c.percent_off == 15
    assert c.active is True
