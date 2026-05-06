# SPDX-License-Identifier: Apache-2.0
"""Auth endpoints: signup, login, logout, password-reset stub, current user."""

from __future__ import annotations

from revar_models.shop_v1.models import User
from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, EmailStr, Field
from sqlmodel import select

from ..auth import create_session, hash_password, verify_password
from ..config import get_settings
from ..deps import CSRF, DB, SessionDep
from ..modifiers import get_config

router = APIRouter()


def _set_session_cookies(response: Response, *, token: str, csrf: str) -> None:
    settings = get_settings()
    cfg = get_config()
    max_age = cfg.session_ttl_s if cfg.session_ttl_s is not None else settings.default_session_ttl_s
    response.set_cookie(
        settings.session_cookie_name,
        token,
        httponly=True,
        samesite="lax",
        max_age=max_age,
        path="/",
    )
    response.set_cookie(
        settings.csrf_cookie_name,
        csrf,
        httponly=False,  # SPA reads this and echoes via X-CSRF-Token
        samesite="lax",
        max_age=max_age,
        path="/",
    )


class SignupPayload(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=120)


@router.post("/api/auth/signup", status_code=201, dependencies=[CSRF])
def signup(payload: SignupPayload, response: Response, db: DB) -> dict:
    existing = db.exec(select(User).where(User.email == str(payload.email))).first()
    if existing is not None:
        raise HTTPException(status_code=409, detail="email_taken")
    user = User(
        email=str(payload.email),
        password_hash=hash_password(payload.password),
        full_name=payload.full_name,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    s = create_session(db, user_id=user.id)
    _set_session_cookies(response, token=s.token, csrf=s.csrf_token)
    return {"id": user.id, "email": user.email, "full_name": user.full_name}


class LoginPayload(BaseModel):
    email: EmailStr
    password: str


@router.post("/api/auth/login", dependencies=[CSRF])
def login(payload: LoginPayload, response: Response, db: DB) -> dict:
    user = db.exec(select(User).where(User.email == str(payload.email))).first()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="invalid_credentials")
    s = create_session(db, user_id=user.id)
    _set_session_cookies(response, token=s.token, csrf=s.csrf_token)
    return {"id": user.id, "email": user.email, "full_name": user.full_name}


@router.post("/api/auth/logout", dependencies=[CSRF])
def logout(response: Response, s: SessionDep, db: DB) -> dict:
    settings = get_settings()
    db.delete(s)
    db.commit()
    response.delete_cookie(settings.session_cookie_name, path="/")
    response.delete_cookie(settings.csrf_cookie_name, path="/")
    return {"ok": True}


@router.get("/api/auth/me")
def me(request: Request, s: SessionDep, db: DB, response: Response) -> dict:
    settings = get_settings()
    # Make sure the cookies are present (e.g. when session was auto-created)
    if not request.cookies.get(settings.session_cookie_name):
        _set_session_cookies(response, token=s.token, csrf=s.csrf_token)
    if s.user_id is None:
        return {"authenticated": False, "csrf_token": s.csrf_token}
    user = db.get(User, s.user_id)
    if user is None:
        return {"authenticated": False, "csrf_token": s.csrf_token}
    return {
        "authenticated": True,
        "user": {"id": user.id, "email": user.email, "full_name": user.full_name},
        "csrf_token": s.csrf_token,
    }


class PasswordResetPayload(BaseModel):
    email: EmailStr


@router.post("/api/auth/password-reset", dependencies=[CSRF])
def password_reset(payload: PasswordResetPayload) -> dict:
    """Stub: real flow would email a reset link. Always returns ok to avoid
    user-enumeration. Tasks that exercise the password-reset path should
    treat this 200 + the displayed instruction screen as success."""
    return {"ok": True, "message": "If the address is registered, you will receive a reset email."}
