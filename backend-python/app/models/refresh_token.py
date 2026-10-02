# backend-python/app/models/refresh_token.py
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.core.database import Base


class RefreshToken(Base):
    """Server-side record of an issued refresh token (the login session).

    Only a SHA-256 hash of the token is stored, so a database leak does not
    hand out usable sessions. Sessions are revocable individually (logout),
    in bulk (logout-all / password change / admin revoke) and rotatable
    (every refresh invalidates the presented token and issues a new one).
    """

    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True, autoincrement=True)

    user_id = Column(
        Integer,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    token_hash = Column(String(64), nullable=False, unique=True, index=True)

    # Token version of the user at issue time; a mismatch with
    # users.token_version means the session has been globally invalidated.
    token_version = Column(Integer, nullable=False, default=0, server_default="0")

    expires_at = Column(DateTime, nullable=False)
    revoked_at = Column(DateTime, nullable=True)
    replaced_by_id = Column(Integer, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_used_at = Column(DateTime, nullable=True)

    user = relationship("User", foreign_keys=[user_id])

    @property
    def is_active(self) -> bool:
        return self.revoked_at is None and self.expires_at > datetime.utcnow()
