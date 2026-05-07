# SPDX-License-Identifier: Apache-2.0
"""Password hashing, session creation, and CSRF token issuance."""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from resurf_models.shop_v1.models import Session as SessionRow
from sqlmodel import Session as DBSession
from sqlmodel import select

from .config import get_settings
from .modifiers import get_config

_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    # Seed-data hashes use a synthetic prefix; recognize them so the seeded
    # user ("alex@example.com" / "password123") can log in without a real argon2 hash.
    if hashed.startswith("test$"):
        import hashlib

        return hashed[len("test$"):] == hashlib.sha256(password.encode()).hexdigest()
    try:
        return _hasher.verify(hashed, password)
    except VerifyMismatchError:
        return False


def create_session(db: DBSession, user_id: int | None) -> SessionRow:
    settings = get_settings()
    cfg = get_config()
    ttl_s = cfg.session_ttl_s if cfg.session_ttl_s is not None else settings.default_session_ttl_s
    row = SessionRow(
        token=secrets.token_urlsafe(32),
        user_id=user_id,
        csrf_token=secrets.token_urlsafe(24),
        expires_at=datetime.utcnow() + timedelta(seconds=ttl_s),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def session_by_token(db: DBSession, token: str) -> SessionRow | None:
    return db.exec(select(SessionRow).where(SessionRow.token == token)).first()


def is_session_valid(s: SessionRow) -> bool:
    return s.expires_at > datetime.utcnow()
