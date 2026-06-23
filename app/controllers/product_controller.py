"""
CONTROLLER: Products
---------------------
Бизнес-логика каталога товаров: CRUD (админ), карточка товара,
управление изображениями/характеристиками и, главное, ПОИСК —
фильтрация, сортировка и пагинация по каталогу (как страницы
категорий/поиска на mi.ua).
"""
import math
from typing import Optional, List, Union
from sqlalchemy.orm import Session
from sqlalchemy import or_, case
from fastapi import HTTPException, status

from app.data.product import Product
from app.data.product_image import ProductImage
from app.data.product_spec import ProductSpecification
from app.data.category import Category
from app.data.brand import Brand
from app.data.user import User
from app.dto.product_schemas import (
    ProductCreateRequest, ProductUpdateRequest, ProductImageCreateRequest,
    ProductSpecificationCreateRequest,
    ProductResponse, ProductCardResponse, ProductListResponse,
    ProductSearchParams, ProductSortOption,
)
from app.utils.helpers import slugify


class ProductController:

    # ── Создание / обновление (админ) ────────────────────────────────────────

    @staticmethod
    def create(payload: ProductCreateRequest, admin: User, db: Session) -> ProductResponse:
        """Создать товар вместе с изображениями и характеристиками."""
        if not db.query(Category).filter(Category.id == payload.category_id).first():
            raise HTTPException(status_code=404, detail="Категория не найдена")
        if payload.brand_id and not db.query(Brand).filter(Brand.id == payload.brand_id).first():
            raise HTTPException(status_code=404, detail="Бренд не найден")
        if payload.sku and db.query(Product).filter(Product.sku == payload.sku).first():
            raise HTTPException(status_code=409, detail=f"Товар с SKU '{payload.sku}' уже существует")

        slug = payload.slug or slugify(payload.name)
        if db.query(Product).filter(Product.slug == slug).first():
            raise HTTPException(status_code=409, detail=f"Товар со slug '{slug}' уже существует")

        data = payload.model_dump(exclude={"images", "specifications", "slug"})
        product = Product(**data, slug=slug, created_by=admin.id)
        db.add(product)
        db.flush()  # получаем product.id до коммита, чтобы привязать дочерние записи

        for img in payload.images:
            db.add(ProductImage(**img.model_dump(), product_id=product.id))
        for spec in payload.specifications:
            db.add(ProductSpecification(**spec.model_dump(), product_id=product.id))

        db.commit()
        db.refresh(product)
        return ProductResponse.model_validate(product)

    @staticmethod
    def update(product_id: int, payload: ProductUpdateRequest, admin: User, db: Session) -> ProductResponse:
        """Обновить товар (требует прав администратора)."""
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product:
            raise HTTPException(status_code=404, detail="Товар не найден")

        update_data = payload.model_dump(exclude_unset=True)

        if "category_id" in update_data and not db.query(Category).filter(Category.id == update_data["category_id"]).first():
            raise HTTPException(status_code=404, detail="Категория не найдена")
        if update_data.get("brand_id") and not db.query(Brand).filter(Brand.id == update_data["brand_id"]).first():
            raise HTTPException(status_code=404, detail="Бренд не найден")
        if "slug" in update_data and update_data["slug"]:
            exists = db.query(Product).filter(Product.slug == update_data["slug"], Product.id != product_id).first()
            if exists:
                raise HTTPException(status_code=409, detail="Такой slug уже занят")
        if "sku" in update_data and update_data["sku"]:
            exists = db.query(Product).filter(Product.sku == update_data["sku"], Product.id != product_id).first()
            if exists:
                raise HTTPException(status_code=409, detail="Такой SKU уже занят")

        for field, value in update_data.items():
            setattr(product, field, value)

        db.commit()
        db.refresh(product)
        return ProductResponse.model_validate(product)

    @staticmethod
    def delete(product_id: int, admin: User, db: Session) -> dict:
        """Soft-delete товара (требует прав администратора)."""
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product:
            raise HTTPException(status_code=404, detail="Товар не найден")

        product.is_active = False
        db.commit()
        return {"message": f"Товар {product_id} деактивирован", "success": True}

    # ── Изображения и характеристики (админ) ─────────────────────────────────

    @staticmethod
    def add_image(product_id: int, payload: ProductImageCreateRequest, admin: User, db: Session) -> ProductResponse:
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product:
            raise HTTPException(status_code=404, detail="Товар не найден")

        db.add(ProductImage(**payload.model_dump(), product_id=product_id))
        db.commit()
        db.refresh(product)
        return ProductResponse.model_validate(product)

    @staticmethod
    def delete_image(product_id: int, image_id: int, admin: User, db: Session) -> dict:
        image = db.query(ProductImage).filter(ProductImage.id == image_id, ProductImage.product_id == product_id).first()
        if not image:
            raise HTTPException(status_code=404, detail="Изображение не найдено")
        db.delete(image)
        db.commit()
        return {"message": "Изображение удалено", "success": True}

    @staticmethod
    def set_specifications(product_id: int, specs: List[ProductSpecificationCreateRequest], admin: User, db: Session) -> ProductResponse:
        """Полностью заменяет таблицу характеристик товара."""
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product:
            raise HTTPException(status_code=404, detail="Товар не найден")

        db.query(ProductSpecification).filter(ProductSpecification.product_id == product_id).delete()
        for spec in specs:
            db.add(ProductSpecification(**spec.model_dump(), product_id=product_id))

        db.commit()
        db.refresh(product)
        return ProductResponse.model_validate(product)

    # ── Получение товара ──────────────────────────────────────────────────────

    @staticmethod
    def _base_query(db: Session, include_inactive: bool = False):
        query = db.query(Product)
        if not include_inactive:
            query = query.filter(Product.is_active == True)
        return query

    @staticmethod
    def get_by_id_or_slug(id_or_slug: Union[int, str], db: Session, count_view: bool = True) -> ProductResponse:
        """Карточка товара по числовому ID или по slug (человекочитаемый URL)."""
        query = ProductController._base_query(db)
        if isinstance(id_or_slug, int) or str(id_or_slug).isdigit():
            product = query.filter(Product.id == int(id_or_slug)).first()
        else:
            product = query.filter(Product.slug == id_or_slug).first()

        if not product:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Товар не найден")

        if count_view:
            product.view_count += 1
            db.commit()
            db.refresh(product)

        return ProductResponse.model_validate(product)

    @staticmethod
    def related(product_id: int, db: Session, limit: int = 8) -> List[ProductCardResponse]:
        """Похожие товары — из той же категории."""
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product:
            raise HTTPException(status_code=404, detail="Товар не найден")

        items = (
            db.query(Product)
            .filter(Product.category_id == product.category_id, Product.id != product_id, Product.is_active == True)
            .limit(limit)
            .all()
        )
        return [ProductCardResponse.model_validate(p) for p in items]

    # ── Поиск / фильтрация / сортировка (главный функционал каталога) ───────

    @staticmethod
    def search(params: ProductSearchParams, db: Session) -> ProductListResponse:
        """
        Поиск товаров — основа страниц каталога mi.ua: категория, бренд,
        диапазон цены, наличие, "новинки"/"топ продаж"/"со скидкой",
        текстовый поиск по названию и описанию, сортировка, пагинация.
        """
        query = ProductController._base_query(db)

        if params.query:
            term = f"%{params.query.lower()}%"
            query = query.filter(or_(Product.name.ilike(term), Product.description.ilike(term)))

        if params.category_slug:
            category = db.query(Category).filter(Category.slug == params.category_slug).first()
            if not category:
                raise HTTPException(status_code=404, detail="Категория не найдена")
            # ищем товары и в самой категории, и во всех её подкатегориях
            category_ids = [category.id] + [c.id for c in category.children]
            query = query.filter(Product.category_id.in_(category_ids))
        elif params.category_id:
            query = query.filter(Product.category_id == params.category_id)

        if params.brand_id:
            query = query.filter(Product.brand_id == params.brand_id)

        if params.min_price is not None:
            query = query.filter(Product.price >= params.min_price)
        if params.max_price is not None:
            query = query.filter(Product.price <= params.max_price)

        if params.in_stock is True:
            query = query.filter(Product.stock > 0)
        elif params.in_stock is False:
            query = query.filter(Product.stock == 0)

        if params.is_new is True:
            query = query.filter(Product.is_new == True)
        if params.is_top is True:
            query = query.filter(Product.is_top == True)
        if params.discounted is True:
            query = query.filter(Product.old_price.isnot(None), Product.old_price > Product.price)

        # Сортировка
        if params.sort == ProductSortOption.NEW:
            query = query.order_by(Product.created_at.desc())
        elif params.sort == ProductSortOption.PRICE_ASC:
            query = query.order_by(Product.price.asc())
        elif params.sort == ProductSortOption.PRICE_DESC:
            query = query.order_by(Product.price.desc())
        elif params.sort == ProductSortOption.RATING:
            query = query.order_by(Product.rating_avg.desc())
        elif params.sort == ProductSortOption.DISCOUNT:
            discount_expr = case(
                (Product.old_price.isnot(None) & (Product.old_price > 0),
                 (Product.old_price - Product.price) / Product.old_price),
                else_=0.0,
            )
            query = query.order_by(discount_expr.desc())
        else:  # POPULAR (по умолчанию)
            query = query.order_by(Product.view_count.desc())

        total = query.count()
        pages = math.ceil(total / params.page_size) if total > 0 else 1
        offset = (params.page - 1) * params.page_size

        items = query.offset(offset).limit(params.page_size).all()

        return ProductListResponse(
            items=[ProductCardResponse.model_validate(p) for p in items],
            total=total,
            page=params.page,
            page_size=params.page_size,
            pages=pages,
        )
