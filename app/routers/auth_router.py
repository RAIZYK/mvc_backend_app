from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.controllers.auth_controller import AuthController
from app.data.base import get_db
from app.data.user import User
from app.dto.auth_schemas import (
    ConfirmRequest,
    LoginRequest,
    MessageResponse,
    RefreshTokenRequest,
    RegisterRequest,
    RegisterStartResponse,
    ResendCodeRequest,
    TokenResponse,
    UserResponse,
)
from app.middleware import get_current_user

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post(
    "/register",
    response_model=RegisterStartResponse,
    status_code=201,
    summary="Шаг 1: регистрация по email",
    description=(
        "Принимает email, пароль и (опционально) имя. Создаёт неактивированный аккаунт "
        "и отправляет 6-значный код подтверждения на почту. "
        "Для завершения регистрации вызовите /auth/register/confirm."
    ),
)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    return AuthController.register(payload, db)


@router.post(
    "/register/confirm",
    response_model=TokenResponse,
    summary="Шаг 2: подтвердить email кодом",
    description="Принимает email + код из письма. При успехе активирует аккаунт и выдаёт токены.",
)
def confirm_register(payload: ConfirmRequest, db: Session = Depends(get_db)):
    return AuthController.confirm(payload, db)


@router.post(
    "/register/resend",
    response_model=RegisterStartResponse,
    summary="Повторно отправить код подтверждения",
)
def resend_code(payload: ResendCodeRequest, db: Session = Depends(get_db)):
    return AuthController.resend_code(payload, db)


@router.post("/login", response_model=TokenResponse, summary="Вход по email и паролю")
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    return AuthController.login(payload, db)


@router.post("/refresh", response_model=TokenResponse, summary="Обновить access/refresh токены")
def refresh(payload: RefreshTokenRequest, db: Session = Depends(get_db)):
    return AuthController.refresh(payload.refresh_token, db)


@router.get("/me", response_model=UserResponse, summary="Данные текущего пользователя")
def get_me(current_user: User = Depends(get_current_user)):
    return AuthController.get_me(current_user)
