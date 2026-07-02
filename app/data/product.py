"""
DATA: Product
--------------
Слой данных — структура таблицы продуктов.
В микросервисной архитектуре переедет в product-service.

Спроектирован по образцу каталога mi.ua: категория + бренд,
старая/новая цена (для бейджа скидки), рейтинг и счётчик отзывов,
флаги "новинка" / "топ продаж", набор изображений (в т.ч. цветовые
варианты товара) и таблица технических характеристик.
"""
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime

from app.data.base import Base


class Product(Base):
    __tablename__ = "products"

    id          = Column(Integer, primary_key=True, index=True)
    name        = Column(String(255), nullable=False, index=True)
    slug        = Column(String(255), unique=True, index=True, nullable=False)
    description = Column(Text, nullable=True)
    short_description = Column(String(500), nullable=True)

    price       = Column(Float, nullable=False)
    old_price   = Column(Float, nullable=True)  # для бейджа скидки (как на mi.ua: было/стало)

    sku         = Column(String(100), unique=True, nullable=True, index=True)
    stock       = Column(Integer, default=0)

    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    brand_id    = Column(Integer, ForeignKey("brands.id"), nullable=True)

    rating_avg    = Column(Float, default=0.0)
    reviews_count = Column(Integer, default=0)
    view_count    = Column(Integer, default=0)

    is_new      = Column(Boolean, default=False)   # секция "Новинки"
    is_top      = Column(Boolean, default=False)   # секция "Лидеры продаж"
    is_active   = Column(Boolean, default=True)    # soft-delete флаг

    # Бейджи карточки товара (как на mi.ua): партнёрская кешбек-программа
    # ("Fishka") и бонусные баллы за отзыв ("+300 За відгук")
    loyalty_partner     = Column(String(100), nullable=True)
    review_bonus_points = Column(Integer, nullable=True)

    created_by  = Column(Integer, ForeignKey("users.id"), nullable=True)  # админ, добавивший товар
    created_at  = Column(DateTime, default=datetime.utcnow)
    updated_at  = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relations
    category       = relationship("Category", back_populates="products")
    brand          = relationship("Brand", back_populates="products")
    images         = relationship("ProductImage", back_populates="product", cascade="all, delete-orphan", order_by="ProductImage.sort_order")
    specifications = relationship("ProductSpecification", back_populates="product", cascade="all, delete-orphan", order_by="ProductSpecification.sort_order")
    reviews        = relationship("Review", back_populates="product", cascade="all, delete-orphan")

    @property
    def discount_percent(self) -> int:
        """Процент скидки, если есть old_price."""
        if self.old_price and self.old_price > self.price:
            return round((1 - self.price / self.old_price) * 100)
        return 0

    @property
    def has_reviews(self) -> bool:
        """Если отзывов нет — фронт показывает ссылку «оставить отзыв» вместо звёзд."""
        return self.reviews_count > 0

    @property
    def main_image(self) -> "str | None":
        """URL главного изображения товара (для карточки в каталоге)."""
        if not self.images:
            return None
        main = next((img for img in self.images if img.is_main), None)
        return (main or self.images[0]).image_url

    def __repr__(self) -> str:
        return f"<Product id={self.id} name={self.name} price={self.price}>"
