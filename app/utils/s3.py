"""
Utils: S3 Image Storage
────────────────────────
Загрузка и удаление изображений через AWS S3 (или совместимые хранилища).

Конфигурируется полностью через ENV:
  AWS_ACCESS_KEY_ID      — ключ доступа
  AWS_SECRET_ACCESS_KEY  — секретный ключ
  AWS_REGION             — регион бакета  (напр. eu-central-1)
  AWS_S3_BUCKET          — имя бакета
  AWS_S3_PUBLIC_URL      — публичный URL бакета (возвращаем в ответе API)
"""
import os
import uuid
import mimetypes
from pathlib import Path
from typing import Optional

import boto3
from botocore.exceptions import ClientError
from fastapi import HTTPException, UploadFile, status

from dotenv import load_dotenv

load_dotenv()

# ─── Конфиг из ENV ────────────────────────────────────────────────────────────
_AWS_ACCESS_KEY_ID     = os.getenv("AWS_ACCESS_KEY_ID")
_AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
_AWS_REGION            = os.getenv("AWS_REGION", "eu-central-1")
_S3_BUCKET             = os.getenv("AWS_S3_BUCKET", "")
_S3_PUBLIC_URL         = os.getenv("AWS_S3_PUBLIC_URL", "").rstrip("/")

# Разрешённые MIME-типы для картинок
_ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
_MAX_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB


def _s3_client():
    """Ленивая инициализация boto3-клиента."""
    if not _AWS_ACCESS_KEY_ID or not _AWS_SECRET_ACCESS_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="S3 не настроен: AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY отсутствуют",
        )
    return boto3.client(
        "s3",
        region_name=_AWS_REGION,
        aws_access_key_id=_AWS_ACCESS_KEY_ID,
        aws_secret_access_key=_AWS_SECRET_ACCESS_KEY,
    )


async def upload_image(file: UploadFile, folder: str = "products") -> str:
    """
    Загружает изображение в S3 и возвращает публичный URL.

    Параметры:
        file   — FastAPI UploadFile из multipart-запроса
        folder — «папка» внутри бакета (products / banners / brands и т.д.)

    Возвращает:
        Полный публичный URL загруженного файла.
    """
    # Проверяем MIME-тип
    content_type = file.content_type or ""
    if content_type not in _ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Неподдерживаемый тип файла: {content_type}. Разрешено: {_ALLOWED_CONTENT_TYPES}",
        )

    # Читаем в память и проверяем размер
    contents = await file.read()
    if len(contents) > _MAX_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Файл слишком большой. Максимум: {_MAX_SIZE_BYTES // (1024 * 1024)} MB",
        )

    # Генерируем уникальное имя файла
    ext = Path(file.filename or "image.jpg").suffix.lower() or ".jpg"
    key = f"{folder}/{uuid.uuid4().hex}{ext}"

    # Загружаем в S3
    try:
        client = _s3_client()
        client.put_object(
            Bucket=_S3_BUCKET,
            Key=key,
            Body=contents,
            ContentType=content_type,
            # ACL="public-read",  # раскомментировать если бакет не Public Access Block
        )
    except ClientError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Ошибка S3: {e.response['Error']['Message']}",
        )

    return f"{_S3_PUBLIC_URL}/{key}"


def delete_image(url: str) -> None:
    """
    Удаляет изображение из S3 по его публичному URL.
    Ошибки логируем, но не пробрасываем — чтобы не блокировать удаление товара.
    """
    if not url.startswith(_S3_PUBLIC_URL):
        return  # не наш файл — не трогаем
    key = url.removeprefix(_S3_PUBLIC_URL + "/")
    try:
        client = _s3_client()
        client.delete_object(Bucket=_S3_BUCKET, Key=key)
    except ClientError:
        pass  # в реальном проекте — логировать через logging/sentry
