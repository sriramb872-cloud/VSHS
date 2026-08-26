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


class UserResponse(BaseModel):
    id: int
    school_id: Optional[int] = None
    mobile: str
    email: Optional[str] = None
    display_name: str
    role: str
    is_active: str

    class Config:
        from_attributes = True