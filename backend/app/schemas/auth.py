from datetime import datetime
from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=160)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: str
    full_name: str
    email: EmailStr
    created_at: datetime
    model_config = {"from_attributes": True}


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut



