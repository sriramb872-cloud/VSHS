# backend-python/app/core/security.py
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

import jwt
from jwt import InvalidTokenError
from passlib.context import CryptContext

from app.core.config import settings

SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create a short-lived signed access token (JWT, PyJWT).

    Callers are expected to include the ``tv`` (token version) claim so the
    server can invalidate every outstanding access token at once - see
    ``app.api.deps.get_current_user``.
    """
    to_encode = data.copy()
    now = datetime.utcnow()
    expire = now + (
        expires_delta
        if expires_delta
        else timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire, "iat": now})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode and validate an access token.

    Returns the payload, or ``None`` when the token is invalid, tampered
    with, or expired (PyJWT validates ``exp`` during decode).
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except InvalidTokenError:
        return None
