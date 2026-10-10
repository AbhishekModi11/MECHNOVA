from datetime import datetime
from typing import Literal
from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr = Field(..., description="Company email address")
    password: str = Field(..., min_length=1, description="Account password")
    role_tab: Literal["admin", "worker"] = Field(..., description="Active login tab (admin or worker)")


class UserOut(BaseModel):
    id: int
    name: str
    company_email: str
    role: str
    company_id: str
    active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
