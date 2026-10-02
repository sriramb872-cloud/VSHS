# backend-python/app/schemas/auth.py
from typing import Optional
from pydantic import BaseModel, Field, model_validator


class LoginRequest(BaseModel):
    mobile: str = Field(..., description="Mobile number, Student ID, Employee ID, or Email used for authentication")
    password: str = Field(..., description="User password")

    @model_validator(mode="before")
    @classmethod
    def accept_mobile_number_alias(cls, values):
        if isinstance(values, dict):
            for key in ["identifier", "username", "student_id", "employee_id", "mobile_number", "login_id"]:
                if key in values and "mobile" not in values:
                    values["mobile"] = values[key]
                    break
            if "mobile" in values and values["mobile"] is not None:
                values["mobile"] = str(values["mobile"]).strip()
        return values


class PasswordChangeRequest(BaseModel):
    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=6, description="New password")


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    must_change_password: bool = False
    # Rotating refresh token for POST /auth/refresh; omitted when the flow
    # only returns an access token.
    refresh_token: Optional[str] = None
    # Access-token lifetime in seconds.
    expires_in: Optional[int] = None
    refresh_token_expires_in: Optional[int] = None


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(..., description="Refresh token issued by /auth/login or /auth/refresh")


class LogoutRequest(BaseModel):
    refresh_token: Optional[str] = Field(None, description="Refresh token to revoke on logout")


class PasswordChangeResponse(TokenResponse):
    message: str


class UserResponse(BaseModel):
    id: int
    school_id: Optional[int] = None
    mobile: str
    email: Optional[str] = None
    display_name: str
    role: str
    is_active: str
    must_change_password: bool = False
    # Set by POST /files/profile-photo. Omitted here, an uploaded photo was
    # stored but never sent back, so no client could display it.
    profile_photo: Optional[str] = None

    class Config:
        from_attributes = True


class ForgotPasswordRequest(BaseModel):
    mobile: Optional[str] = Field(None, description="Mobile number of the account")
    email: Optional[str] = Field(None, description="Email of the account")

    @model_validator(mode="after")
    def require_one_identifier(self):
        if not self.mobile and not self.email:
            raise ValueError("Provide either mobile or email")
        return self


class ResetPasswordRequest(BaseModel):
    reset_token: str = Field(..., description="Token issued by /auth/forgot-password")
    new_password: str = Field(..., min_length=6, description="New password")

