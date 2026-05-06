# SPDX-License-Identifier: Apache-2.0
"""FastAPI dependency providers: db session, current session, current user, csrf check."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, status
from revar_models.shop_v1.models import Session as SessionRow
from revar_models.shop_v1.models import User
from sqlmodel import Session as DBSession
from sqlmodel import create_engine

from .auth import create_session, is_session_valid, session_by_token
from .config import get_settings

_engine = None


def get_engine():
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_engine(settings.database_url, connect_args={"check_same_thread": False})
    return _engine


def reset_engine() -> None:
    """Used by /__test__/reset to drop pooled connections after a file swap."""
    global _engine
    if _engine is not None:
        _engine.dispose()
        _engine = None


def get_db() -> Iterator[DBSession]:
    engine = get_engine()
    with DBSession(engine) as db:
        yield db


DB = Annotated[DBSession, Depends(get_db)]


def session_dep(
    request: Request,
    db: DB,
) -> SessionRow:
    """Resolve (or auto-create) the current session row from cookies."""
    settings = get_settings()
    token = request.cookies.get(settings.session_cookie_name)
    if token is None:
        return create_session(db, user_id=None)
    s = session_by_token(db, token)
    if s is None or not is_session_valid(s):
        return create_session(db, user_id=None)
    return s


SessionDep = Annotated[SessionRow, Depends(session_dep)]


def current_user_required(
    s: SessionDep,
    db: DB,
) -> User:
    if s.user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="not_authenticated")
    user = db.get(User, s.user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="not_authenticated")
    return user


CurrentUser = Annotated[User, Depends(current_user_required)]


def csrf_check(
    request: Request,
    s: SessionDep,
    x_csrf_token: str | None = Header(default=None, alias="X-CSRF-Token"),
) -> None:
    """Mutating routes must present the CSRF token from the session.

    We use the double-submit pattern: token is set in a non-HttpOnly cookie at
    session creation and the SPA echoes it via the X-CSRF-Token header.
    GET/HEAD/OPTIONS are exempt by FastAPI not calling this dep on them.
    """
    if request.method in ("GET", "HEAD", "OPTIONS"):
        return
    if not x_csrf_token or x_csrf_token != s.csrf_token:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="csrf_invalid")


CSRF = Depends(csrf_check)
