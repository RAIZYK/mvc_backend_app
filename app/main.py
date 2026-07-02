from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.data.base import Base, engine
from app.data import otp, user  # noqa: F401  (регистрируем модели в metadata)
from app.routers.auth_router import router as auth_router

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Auth Service",
    description="Микросервис аутентификации: регистрация по email с подтверждением кодом, логин, JWT.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)


@app.get("/", tags=["Health"])
def root():
    return {"status": "ok", "service": "auth-service", "version": "1.0.0"}


@app.get("/health", tags=["Health"])
def health():
    return {"status": "healthy"}
