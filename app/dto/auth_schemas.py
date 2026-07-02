"""
DTO: Auth
─────────
Pydantic-схемы для Auth-контроллера.
"""
from pydantic import BaseModel, EmailStr, field_validator
from datetime import datetime
from typing import Optional
import re


# ── Регистрация ───────────────────────────────────────────────────────────────

class UserRegisterRequest(BaseModel):
    email: EmailStr
    username: str
    phone: Optional[str] = None
    full_name: Optional[str] = None
    password: str
    password_confirm: str

    @field_validator("username")
    @classmethod
    def username_valid(cls, v: str) -> str:
        if len(v) < 3:
            raise ValueError("Username минимум 3 символа")
        if not re.match(r"^[a-zA-Z0-9_]+$", v):
            raise ValueError("Username: только буквы, цифры, _")
        return v

    @field_validator("phone")
    @classmethod
    def phone_valid(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v == "":
            return None
        if not re.match(r"^\+?[0-9]{10,15}$", v):
            raise ValueError("Телефон должен быть в формате +380XXXXXXXXX")
        return v

    @field_validator("password")
    @classmethod
    def password_strong(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Пароль минимум 8 символов")
        return v

    @field_validator("password_confirm")
    @classmethod
    def passwords_match(cls, v: str, info) -> str:
        if "password" in info.data and v != info.data["password"]:
            raise ValueError("Пароли не совпадают")
        return v


# ── Логин ─────────────────────────────────────────────────────────────────────

class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str


# ── Обновление профиля ────────────────────────────────────────────────────────

class UserUpdateRequest(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def password_strong(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Пароль минимум 8 символов")
        return v


# ── Ответы ────────────────────────────────────────────────────────────────────

class UserResponse(BaseModel):
    id: int
    email: str
    username: str
    phone: Optional[str] = None
    full_name: Optional[str] = None
    role: str
    is_active: bool
    is_verified: bool
    created_at: datetime

    model_config = {"from_attributes": True}

    @field_validator("role", mode="before")
    @classmethod
    def role_to_str(cls, v):
        return v.value if hasattr(v, "value") else v


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str          # добавлен refresh token
    token_type: str = "bearer"
    user: UserResponse


class MessageResponse(BaseModel):
    message: str
    success: bool = True
