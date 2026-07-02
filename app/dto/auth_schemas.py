import re
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, field_validator

EMAIL_RE = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


# ──────────────────────────────────────────────
# Регистрация — шаг 1: email + пароль
# ──────────────────────────────────────────────

class RegisterRequest(BaseModel):
    """
    Шаг 1: пользователь вводит email, пароль и (опционально) имя.
    Создаётся неактивированный аккаунт (is_verified=False),
    на почту отправляется 6-значный код подтверждения.
    """
    email: str
    full_name: Optional[str] = None
    password: str
    password_confirm: str

    @field_validator("email")
    @classmethod
    def email_valid(cls, v: str) -> str:
        v = v.strip().lower()
        if not re.match(EMAIL_RE, v):
            raise ValueError("Некорректный формат email")
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


class RegisterStartResponse(BaseModel):
    message: str
    email: str
    expires_in_minutes: int


# ──────────────────────────────────────────────
# Регистрация — шаг 2: подтверждение кода
# ──────────────────────────────────────────────

class ConfirmRequest(BaseModel):
    email: str
    code: str

    @field_validator("email")
    @classmethod
    def email_valid(cls, v: str) -> str:
        v = v.strip().lower()
        if not re.match(EMAIL_RE, v):
            raise ValueError("Некорректный формат email")
        return v

    @field_validator("code")
    @classmethod
    def code_valid(cls, v: str) -> str:
        v = v.strip()
        if not v.isdigit() or len(v) != 6:
            raise ValueError("Код должен состоять из 6 цифр")
        return v


class ResendCodeRequest(BaseModel):
    email: str

    @field_validator("email")
    @classmethod
    def email_valid(cls, v: str) -> str:
        v = v.strip().lower()
        if not re.match(EMAIL_RE, v):
            raise ValueError("Некорректный формат email")
        return v


# ──────────────────────────────────────────────
# Логин / токены
# ──────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def email_valid(cls, v: str) -> str:
        v = v.strip().lower()
        if not re.match(EMAIL_RE, v):
            raise ValueError("Некорректный формат email")
        return v


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class UserResponse(BaseModel):
    id: int
    email: str
    full_name: Optional[str] = None
    is_active: bool
    is_verified: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse


class MessageResponse(BaseModel):
    message: str
    success: bool = True
