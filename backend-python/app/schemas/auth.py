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
    """Step 1 of the reset flow.

    ``login_id`` is the same identifier the sign-in form accepts (mobile,
    email, student ID or employee ID); the legacy field names are still
    accepted so older clients keep working.
    """

    login_id: str = Field(
        ...,
        min_length=1,
        description="Mobile number, email address, student ID, or employee ID",
    )

    @model_validator(mode="before")
    @classmethod
    def accept_legacy_identifier_aliases(cls, values):
        if isinstance(values, dict):
            for key in (
                "login_id",
                "identifier",
                "username",
                "student_id",
                "employee_id",
                "mobile_number",
                "mobile",
                "email",
            ):
                if values.get(key) not in (None, "") and not str(values.get("login_id") or "").strip():
                    values["login_id"] = values[key]
                    break
            if values.get("login_id") is not None:
                values["login_id"] = str(values["login_id"]).strip()
            if values.get("otp") is not None:
                values["otp"] = str(values["otp"]).strip()
        return values


class VerifyResetOtpRequest(ForgotPasswordRequest):
    """Step 2: prove the code from the mail, receive a short-lived reset token."""

    otp: str = Field(
        ...,
        min_length=1,
        max_length=32,
        description="6-digit code from the password reset email",
    )


class ResetPasswordRequest(BaseModel):
    """Step 3: spend the single-use token issued by verify-reset-otp.

    Strength is validated server-side (``validate_password_strength``) so the
    user gets one precise message instead of a generic 422.
    """

    reset_token: str = Field(..., min_length=1, description="Token issued by /auth/verify-reset-otp")
    new_password: str = Field(..., min_length=1, description="New password")

