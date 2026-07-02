"""
Utils: JWT + Password hashing
──────────────────────────────
Все секреты читаются из ENV (через .env файл).
Поддерживает access-token + refresh-token.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional, Literal
import os

from dotenv import load_dotenv
from jose import JWTError, jwt
from passlib.context import CryptContext

load_dotenv()  # читает .env если он есть (в продакшне переменные выставляются в системе)

# ─── Конфигурация из ENV ──────────────────────────────────────────────────────
SECRET_KEY: str = os.environ["SECRET_KEY"]          # обязательно — упадём при старте если нет
ALGORITHM: str  = os.getenv("ALGORITHM", "HS256")

ACCESS_TOKEN_EXPIRE_MINUTES: int  = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
REFRESH_TOKEN_EXPIRE_DAYS:   int  = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS",   "30"))

# ─── Хэширование паролей ─────────────────────────────────────────────────────
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


# ─── JWT ─────────────────────────────────────────────────────────────────────

def _create_token(
    data: dict,
    token_type: Literal["access", "refresh"],
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Внутренняя фабрика токенов. type кладём в payload для явного разграничения."""
    if expires_delta is None:
        if token_type == "access":
            expires_delta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        else:
            expires_delta = timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

    now = datetime.now(tz=timezone.utc)
    payload = {
        **data,
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Короткоживущий токен для API-запросов (по умолчанию 60 мин)."""
    return _create_token(data, "access", expires_delta)


def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Долгоживущий токен для обновления access-токена (по умолчанию 30 дней)."""
    return _create_token(data, "refresh", expires_delta)


def decode_token(token: str, expected_type: Optional[Literal["access", "refresh"]] = None) -> Optional[dict]:
    """
    Декодирует и валидирует JWT.
    Если expected_type задан — проверяет поле type в payload.
    Возвращает None при любой ошибке (невалидный подпись, истёк, неверный тип).
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if expected_type and payload.get("type") != expected_type:
            return None
        return payload
    except JWTError:
        return None
