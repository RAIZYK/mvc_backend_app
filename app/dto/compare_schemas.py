"""
DTO: Compare (сравнение товаров)
----------------------------------------------
"""
from pydantic import BaseModel
from typing import List, Dict
from app.dto.product_schemas import ProductCardResponse


class CompareSpecRow(BaseModel):
    group_name: str
    name: str
    values: Dict[str, str]  # product_id (str) -> значение характеристики (пусто, если нет)


class CompareResponse(BaseModel):
    products: List[ProductCardResponse]
    specifications: List[CompareSpecRow]
