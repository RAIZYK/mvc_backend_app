import random
import string
from datetime import datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.data.otp import EmailOtp
from app.data.user import User
from app.dto.auth_schemas import (
    ConfirmRequest,
    LoginRequest,
    MessageResponse,
    RegisterRequest,
    RegisterStartResponse,
    ResendCodeRequest,
    TokenResponse,
    UserResponse,
)
from app.utils.email import email_service
from app.utils.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)


def _build_token_response(user: User) -> TokenResponse:
    sub = {"sub": str(user.id)}
    return TokenResponse(
        access_token=create_access_token(sub),
        refresh_token=create_refresh_token(sub),
        user=UserResponse.model_validate(user),
    )


def _generate_code() -> str:
    return "".join(random.choices(string.digits, k=settings.OTP_CODE_LENGTH))


def _issue_code(db: Session, email: str) -> None:
    """Аннулирует старые коды для email и выпускает/отправляет новый."""
    db.query(EmailOtp).filter(
        EmailOtp.email == email,
        EmailOtp.is_used == False,  # noqa: E712
    ).delete()
    db.commit()

    code = _generate_code()
    otp = EmailOtp(
        email=email,
        code=code,
        expires_at=datetime.utcnow() + timedelta(minutes=settings.OTP_EXPIRE_MINUTES),
    )
    db.add(otp)
    db.commit()

    try:
        email_service.send_otp(email, code, settings.OTP_EXPIRE_MINUTES)
    except Exception as e:
        db.delete(otp)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Не удалось отправить письмо: {str(e)}",
        )


class AuthController:

    # ──────────────────────────────────────────
    # Шаг 1: регистрация
    # ──────────────────────────────────────────

    @staticmethod
    def register(payload: RegisterRequest, db: Session) -> RegisterStartResponse:
        existing = db.query(User).filter(User.email == payload.email).first()

        if existing and existing.is_verified:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email уже зарегистрирован",
            )

        if existing and not existing.is_verified:
            existing.full_name = payload.full_name
            existing.hashed_password = hash_password(payload.password)
            db.commit()
        else:
            user = User(
                email=payload.email,
                full_name=payload.full_name,
                hashed_password=hash_password(payload.password),
                is_verified=False,
            )
            db.add(user)
            db.commit()

        _issue_code(db, payload.email)

        return RegisterStartResponse(
            message=f"Код подтверждения отправлен на {payload.email}",
            email=payload.email,
            expires_in_minutes=settings.OTP_EXPIRE_MINUTES,
        )

    # ──────────────────────────────────────────
    # Шаг 2: подтверждение кода
    # ──────────────────────────────────────────

    @staticmethod
    def confirm(payload: ConfirmRequest, db: Session) -> TokenResponse:
        otp = (
            db.query(EmailOtp)
            .filter(
                EmailOtp.email == payload.email,
                EmailOtp.code == payload.code,
                EmailOtp.is_used == False,  # noqa: E712
            )
            .order_by(EmailOtp.created_at.desc())
            .first()
        )

        if otp is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Неверный код подтверждения",
            )
        if datetime.utcnow() > otp.expires_at:
            otp.is_used = True
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Срок действия кода истёк. Запросите новый.",
            )

        user = db.query(User).filter(User.email == payload.email).first()
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Сначала пройдите регистрацию (укажите email и пароль)",
            )

        otp.is_used = True
        user.is_verified = True
        db.commit()
        db.refresh(user)

        try:
            email_service.send_welcome(user.email, user.full_name)
        except Exception:
            pass

        return _build_token_response(user)

    # ──────────────────────────────────────────
    # Повторная отправка кода
    # ──────────────────────────────────────────

    @staticmethod
    def resend_code(payload: ResendCodeRequest, db: Session) -> RegisterStartResponse:
        user = db.query(User).filter(User.email == payload.email).first()
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Пользователь с таким email не найден. Зарегистрируйтесь сначала.",
            )
        if user.is_verified:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email уже подтверждён, можно войти в аккаунт",
            )

        _issue_code(db, payload.email)

        return RegisterStartResponse(
            message=f"Код подтверждения повторно отправлен на {payload.email}",
            email=payload.email,
            expires_in_minutes=settings.OTP_EXPIRE_MINUTES,
        )

    # ──────────────────────────────────────────
    # Логин
    # ──────────────────────────────────────────

    @staticmethod
    def login(payload: LoginRequest, db: Session) -> TokenResponse:
        user = db.query(User).filter(User.email == payload.email).first()

        if user is None or not verify_password(payload.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Неверный email или пароль",
            )
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Аккаунт деактивирован",
            )
        if not user.is_verified:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Email не подтверждён. Завершите регистрацию по коду из письма.",
            )
        return _build_token_response(user)

    # ──────────────────────────────────────────
    # Обновление токенов
    # ──────────────────────────────────────────

    @staticmethod
    def refresh(refresh_token: str, db: Session) -> TokenResponse:
        payload = decode_token(refresh_token, expected_type="refresh")
        if payload is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Невалидный или истёкший refresh-токен",
            )
        user_id = payload.get("sub")
        user = db.query(User).filter(User.id == int(user_id)).first()
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Пользователь не найден",
            )
        return _build_token_response(user)

    # ──────────────────────────────────────────
    # Текущий пользователь
    # ──────────────────────────────────────────

    @staticmethod
    def get_me(current_user: User) -> UserResponse:
        return UserResponse.model_validate(current_user)
