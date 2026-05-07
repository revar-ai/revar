# SPDX-License-Identifier: Apache-2.0
"""Deterministic seed data for shop_v1.

A given seed integer produces byte-for-byte identical data. This is the
foundation of reproducibility: tasks reference seeded objects by name/slug
and success_fn predicates run against a known initial state.
"""

from __future__ import annotations

import hashlib
import random
from datetime import datetime

from faker import Faker
from sqlmodel import Session as DBSession
from sqlmodel import SQLModel, create_engine, select

from .models import (
    Address,
    Category,
    Coupon,
    Product,
    User,
)

# Hand-curated category list so seeds are stable and tasks are easy to write.
CATEGORIES = [
    ("audio", "Audio", "Headphones, speakers, and earbuds."),
    ("wearables", "Wearables", "Smartwatches and fitness trackers."),
    ("home", "Home", "Smart home, lighting, and small appliances."),
    ("fragrance", "Fragrance", "Perfumes, colognes, and home scents."),
    ("apparel", "Apparel", "Tops, bottoms, and accessories."),
    ("outdoors", "Outdoors", "Bags, bottles, and gear."),
]

# A small set of hand-picked anchor products that tasks reference by name.
# These are guaranteed to exist in every seed and have predictable attributes.
ANCHOR_PRODUCTS = [
    {
        "slug": "acme-bluetooth-speaker",
        "name": "Acme Bluetooth Speaker",
        "category": "audio",
        "price_cents": 7999,
        "stock": 25,
        "tags": "bluetooth,portable,wireless",
        "rating": 4.5,
        "rating_count": 312,
    },
    {
        "slug": "acme-pro-headphones",
        "name": "Acme Pro Headphones",
        "category": "audio",
        "price_cents": 24999,
        "stock": 12,
        "tags": "noise-cancelling,wireless,over-ear",
        "rating": 4.7,
        "rating_count": 856,
    },
    {
        "slug": "lumen-smart-bulb",
        "name": "Lumen Smart Bulb",
        "category": "home",
        "price_cents": 1499,
        "stock": 0,  # deliberately out of stock
        "tags": "smart-home,led,wifi",
        "rating": 4.2,
        "rating_count": 198,
    },
    {
        "slug": "trailmate-water-bottle",
        "name": "TrailMate Water Bottle",
        "category": "outdoors",
        "price_cents": 2999,
        "stock": 80,
        "tags": "stainless,insulated,outdoor",
        "rating": 4.6,
        "rating_count": 421,
    },
    {
        "slug": "northwood-pulse-watch",
        "name": "Northwood Pulse Watch",
        "category": "wearables",
        "price_cents": 19999,
        "stock": 8,
        "tags": "smartwatch,fitness,heart-rate",
        "rating": 4.4,
        "rating_count": 267,
    },
    {
        "slug": "saffron-no-7-eau-de-parfum",
        "name": "Saffron No.7 Eau de Parfum",
        "category": "fragrance",
        "price_cents": 8999,
        "stock": 30,
        "tags": "unisex,floral,50ml",
        "rating": 4.3,
        "rating_count": 144,
    },
    {
        "slug": "saffron-no-7-travel-spray",
        "name": "Saffron No.7 Travel Spray",
        "category": "fragrance",
        "price_cents": 3499,
        "stock": 50,
        "tags": "unisex,floral,10ml",
        "rating": 4.1,
        "rating_count": 88,
    },
]

# Coupons that tasks reference by name. SUMMER15 is the canonical example.
COUPONS = [
    {
        "code": "SUMMER15",
        "description": "15% off your order",
        "percent_off": 15,
        "min_subtotal_cents": 0,
    },
    {
        "code": "WELCOME10",
        "description": "$10 off orders over $50",
        "percent_off": 0,
        "flat_off_cents": 1000,
        "min_subtotal_cents": 5000,
    },
    {
        "code": "FRAGRANCE20",
        "description": "20% off fragrance",
        "percent_off": 20,
        "min_subtotal_cents": 0,
    },
    {
        "code": "EXPIRED5",
        "description": "Expired test coupon",
        "percent_off": 5,
        "expires_at": datetime(2020, 1, 1),
        "active": False,
    },
]


def _password_hash(plaintext: str) -> str:
    # Trivial hash for synthetic data. The site backend uses argon2 for real
    # password verification; this just gives us a stable hash in the seed file.
    return "test$" + hashlib.sha256(plaintext.encode()).hexdigest()


def seed_database(database_url: str, seed: int = 42) -> None:
    """Wipe and reseed the database. Idempotent for a given seed integer."""
    engine = create_engine(database_url)
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)

    fake = Faker()
    Faker.seed(seed)
    rng = random.Random(seed)

    with DBSession(engine) as db:
        # Categories
        cats: dict[str, Category] = {}
        for slug, name, desc in CATEGORIES:
            c = Category(slug=slug, name=name, description=desc)
            db.add(c)
            cats[slug] = c
        db.flush()

        # Anchor products
        for ap in ANCHOR_PRODUCTS:
            p = Product(
                slug=ap["slug"],
                name=ap["name"],
                description=fake.paragraph(nb_sentences=4),
                short_description=fake.sentence(nb_words=12),
                price_cents=ap["price_cents"],
                stock=ap["stock"],
                image_url=f"/static/products/{ap['slug']}.jpg",
                category_id=cats[ap["category"]].id,  # type: ignore[arg-type]
                rating=ap["rating"],
                rating_count=ap["rating_count"],
                tags=ap["tags"],
            )
            db.add(p)

        # Filler products so the catalog is realistic-feeling, not 7 items.
        for _ in range(60):
            cat_slug = rng.choice(list(cats.keys()))
            name = fake.unique.catch_phrase()[:48]
            slug = name.lower().replace(" ", "-").replace("/", "-").replace(",", "")[:64]
            db.add(
                Product(
                    slug=slug,
                    name=name,
                    description=fake.paragraph(nb_sentences=3),
                    short_description=fake.sentence(nb_words=10),
                    price_cents=rng.randint(999, 49999),
                    stock=rng.randint(0, 100),
                    image_url=f"/static/products/placeholder-{rng.randint(1, 12)}.jpg",
                    category_id=cats[cat_slug].id,  # type: ignore[arg-type]
                    rating=round(rng.uniform(3.0, 5.0), 1),
                    rating_count=rng.randint(0, 1500),
                    tags=",".join(fake.words(nb=3, unique=True)),
                )
            )

        # Coupons
        for c in COUPONS:
            db.add(Coupon(**c))

        # The seeded test user
        user = User(
            email="alex@example.com",
            password_hash=_password_hash("password123"),
            full_name="Alex Doe",
            created_at=datetime(2025, 1, 1),
        )
        db.add(user)
        db.flush()

        # Default address
        db.add(
            Address(
                user_id=user.id,  # type: ignore[arg-type]
                label="home",
                full_name="Alex Doe",
                line1="100 Test Street",
                city="San Francisco",
                state="CA",
                postal_code="94110",
                country="US",
                is_default=True,
            )
        )
        # A second address so "saved address" tasks have something to disambiguate
        db.add(
            Address(
                user_id=user.id,  # type: ignore[arg-type]
                label="work",
                full_name="Alex Doe",
                line1="500 Market Street",
                line2="Floor 14",
                city="San Francisco",
                state="CA",
                postal_code="94105",
                country="US",
                is_default=False,
            )
        )

        db.commit()


def seeded_user_id(database_url: str) -> int:
    """Convenience helper: returns the id of the seeded test user."""
    engine = create_engine(database_url)
    with DBSession(engine) as db:
        u = db.exec(select(User).where(User.email == "alex@example.com")).first()
        if u is None or u.id is None:
            raise RuntimeError("Seeded user not found; run seed_database first.")
        return u.id


__all__ = ["ANCHOR_PRODUCTS", "CATEGORIES", "COUPONS", "seed_database", "seeded_user_id"]
