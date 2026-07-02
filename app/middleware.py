from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.data.base import get_db
from app.data.user import User
from app.utils.security import decode_token

bearer_scheme = HTTPBearer(auto_error=False)


def _user_from_token(token: Optional[str], db: Session) -> Optional[User]:
    if not token:
        return None
    payload = decode_token(token, expected_type="access")
    if payload is None:
        return None
    user_id = payload.get("sub")
    if user_id is None:
        return None
    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None or not user.is_active:
        return None
    return user


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Требуется авторизация",
        )
    user = _user_from_token(credentials.credentials, db)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Невалидный или истёкший токен",
        )
    return user
