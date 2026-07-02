"""
ROUTER: /upload
───────────────
Загрузка изображений в S3.
Доступно только администраторам (для загрузки фото товаров, баннеров и т.д.).
"""
from fastapi import APIRouter, Depends, UploadFile, File, Query
from typing import Literal

from app.data.user import User
from app.middleware.auth import require_admin
from app.utils.s3 import upload_image

router = APIRouter(prefix="/upload", tags=["Upload"])


class ImageUploadResponse:
    def __init__(self, url: str):
        self.url = url


@router.post("/image", summary="Загрузить изображение в S3")
async def upload_image_endpoint(
    file: UploadFile = File(..., description="Изображение (jpg/png/webp/gif, макс. 10 MB)"),
    folder: Literal["products", "banners", "brands", "categories"] = Query(
        default="products",
        description="Папка в S3-бакете",
    ),
    _admin: User = Depends(require_admin),
):
    """
    Загружает изображение в S3 и возвращает публичный URL.

    URL можно затем использовать при создании/обновлении товара, бренда и т.д.
    Пример:
    ```
    POST /upload/image?folder=products
    Content-Type: multipart/form-data
    Authorization: Bearer <admin_access_token>

    → { "url": "https://bucket.s3.region.amazonaws.com/products/abc123.jpg" }
    ```
    """
    url = await upload_image(file, folder=folder)
    return {"url": url}
