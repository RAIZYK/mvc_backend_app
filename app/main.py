"""
MAIN: FastAPI Application
-------------------------
Точка входа. Подключает роутеры, инициализирует БД и (при пустой БД)
заполняет её демонстрационными данными в стиле каталога mi.ua.
"""
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.data.base import Base, engine, SessionLocal
from app.data import *  # noqa: регистрируем все модели перед create_all
from app.data.seed import seed_database
from app.routers import auth_router, product_router, category_router, brand_router, upload_router

# Создаём таблицы (в продакшне — через Alembic миграции)
Base.metadata.create_all(bind=engine)

# Демонстрационные данные (категории/бренды/товары) — только если БД пуста
with SessionLocal() as _db:
    seed_database(_db)

app = FastAPI(
    title="MI-Shop Backend",
    description=(
        "Backend интернет-магазина электроники по образцу mi.ua. "
        "Auth + Каталог (категории, бренды, товары, поиск/фильтры). "
        "MVC-архитектура, готово к разбивке на микросервисы "
        "(auth-service / catalog-service)."
    ),
    version="2.0.0",
)

# CORS — открыт для демо-фронтенда / разработки
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В продакшне — список конкретных доменов
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Роутеры
app.include_router(auth_router.router)
app.include_router(category_router.router)
app.include_router(brand_router.router)
app.include_router(product_router.router)
app.include_router(upload_router.router)

# Демо-фронтенд (статическая страница, обращающаяся к API ниже) — /demo
_frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
if _frontend_dir.exists():
    app.mount("/demo", StaticFiles(directory=str(_frontend_dir), html=True), name="demo")


@app.get("/", tags=["Health"])
def root():
    return {"status": "ok", "version": "2.0.0", "demo_frontend": "/demo"}


@app.get("/health", tags=["Health"])
def health():
    return {"status": "healthy"}
