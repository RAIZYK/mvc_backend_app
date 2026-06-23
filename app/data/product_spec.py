"""
DATA: ProductSpecification
---------------------------
Технические характеристики товара, сгруппированные по разделам
(«Экран», «Память», «Камера» и т.д.) — как таблица характеристик
на карточке товара mi.ua.
"""
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship

from app.data.base import Base


class ProductSpecification(Base):
    __tablename__ = "product_specifications"

    id          = Column(Integer, primary_key=True, index=True)
    product_id  = Column(Integer, ForeignKey("products.id"), nullable=False)

    group_name  = Column(String(150), nullable=False)   # напр. "Экран"
    name        = Column(String(150), nullable=False)   # напр. "Диагональ"
    value       = Column(String(255), nullable=False)   # напр. "6.67\""
    sort_order  = Column(Integer, default=0)

    product = relationship("Product", back_populates="specifications")

    def __repr__(self) -> str:
        return f"<ProductSpecification {self.name}={self.value}>"
