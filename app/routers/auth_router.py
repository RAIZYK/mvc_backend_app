"""
ROUTER: /auth
─────────────
HTTP-слой — маршрутизация запросов к AuthController.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.data.base import get_db
from app.data.user import User
from app.dto.auth_schemas import (
    UserRegisterRequest, UserLoginRequest, UserUpdateRequest, ChangePasswordRequest,
    RefreshTokenRequest, TokenResponse, UserResponse, MessageResponse,
)
from app.controllers.auth_controller import AuthController
from app.middleware.auth import get_current_user

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=TokenResponse, status_code=201)
def register(payload: UserRegisterRequest, db: Session = Depends(get_db)):
    """Регистрация. Возвращает access + refresh токены."""
    return AuthController.register(payload, db)


@router.post("/login", response_model=TokenResponse)
def login(payload: UserLoginRequest, db: Session = Depends(get_db)):
    """Логин по email + паролю. Возвращает access + refresh токены."""
    return AuthController.login(payload, db)


@router.post("/refresh", response_model=TokenResponse)
def refresh(payload: RefreshTokenRequest, db: Session = Depends(get_db)):
    """
    Обновляет пару токенов по refresh_token.
    Клиент вызывает когда access_token истёк (401).
    """
    return AuthController.refresh(payload.refresh_token, db)


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """Профиль текущего авторизованного пользователя."""
    return AuthController.get_me(current_user)


@router.patch("/me", response_model=UserResponse)
def update_me(
    payload: UserUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Обновить имя/телефон."""
    return AuthController.update_me(payload, current_user, db)


@router.post("/change-password", response_model=MessageResponse)
def change_password(
    payload: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Смена пароля (требуется текущий пароль)."""
    return AuthController.change_password(payload, current_user, db)
