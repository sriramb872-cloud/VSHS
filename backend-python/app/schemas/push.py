# app/schemas/push.py
from pydantic import BaseModel, Field


class PushKeys(BaseModel):
    """The browser's push subscription keys (PushSubscription.toJSON())."""

    p256dh: str = Field(..., min_length=1, description="Base64url-encoded P-256 public key")
    auth: str = Field(..., min_length=1, description="Base64url-encoded auth secret")


class PushSubscribeRequest(BaseModel):
    endpoint: str = Field(..., min_length=1, max_length=4096)
    keys: PushKeys


class PushUnsubscribeRequest(BaseModel):
    endpoint: str = Field(..., min_length=1, max_length=4096)


class PushPublicKeyResponse(BaseModel):
    public_key: str
    enabled: bool
