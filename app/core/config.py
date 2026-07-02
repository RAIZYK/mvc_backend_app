from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ── Сервис ────────────────────────────────
    SERVICE_NAME: str = "Auth Service"

    # ── База данных ───────────────────────────
    DATABASE_URL: str = "sqlite:///./auth.db"

    # ── JWT ───────────────────────────────────
    SECRET_KEY: str = "CHANGE_ME"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # ── SMTP (Gmail) ──────────────────────────
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_SENDER_NAME: str = "My Shop"

    # ── OTP ───────────────────────────────────
    OTP_EXPIRE_MINUTES: int = 10
    OTP_CODE_LENGTH: int = 6

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
