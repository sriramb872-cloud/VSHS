"""Small shared test helpers."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.token_service import issue_session
from app.models.user import User


def auth(db: Session, user: User) -> dict:
    """Authorization headers with a freshly minted, real access token.

    Goes through ``issue_session`` (the production code path) but skips
    bcrypt, which keeps the tenant suite fast; login itself is covered
    end-to-end in ``tests/test_auth.py``.
    """
    pair = issue_session(db, user)
    return {"Authorization": f"Bearer {pair['access_token']}"}
