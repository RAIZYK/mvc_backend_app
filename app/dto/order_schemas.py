"""
DTO: Order
-----------------------
Оформление заказа (checkout), список и детали заказов, смена статуса (админ).
"""
from pydantic import BaseModel, field_validator
from datetime import datetime
from typing import Optional, List


class OrderItemCreateRequest(BaseModel):
    """Используется только при checkout без корзины (заказ "в один клик")."""
    product_id: int
    quantity: int = 1


class OrderCreateRequest(BaseModel):
    full_name: str
    phone: str
    email: Optional[str] = None
    city: str
    delivery_method: str  # courier | nova_poshta | pickup
    delivery_address: Optional[str] = None
    store_id: Optional[int] = None
    payment_method: str   # card_online | cash_on_delivery | card_on_delivery
    comment: Optional[str] = None
    # Если items не передан — заказ собирается из текущей корзины пользователя/сессии.
    items: Optional[List[OrderItemCreateRequest]] = None

    @field_validator("phone")
    @classmethod
    def phone_valid(cls, v: str) -> str:
        import re
        if not re.match(r"^\+?[0-9]{10,15}$", v):
            raise ValueError("Телефон должен быть в формате +380XXXXXXXXX")
        return v


class OrderStatusUpdateRequest(BaseModel):
    status: str  # new | confirmed | processing | shipped | delivered | cancelled


class OrderItemResponse(BaseModel):
    id: int
    product_id: Optional[int]
    product_name: str
    product_image: Optional[str]
    price: float
    quantity: int
    subtotal: float

    model_config = {"from_attributes": True}


class OrderResponse(BaseModel):
    id: int
    order_number: str
    full_name: str
    phone: str
    email: Optional[str]
    city: str
    delivery_method: str
    delivery_address: Optional[str]
    store_id: Optional[int]
    payment_method: str
    comment: Optional[str]
    status: str
    total_amount: float
    items: List[OrderItemResponse]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @field_validator("delivery_method", "payment_method", "status", mode="before")
    @classmethod
    def enum_to_str(cls, v):
        return v.value if hasattr(v, "value") else v


class OrderListResponse(BaseModel):
    items: List[OrderResponse]
    total: int
    page: int
    page_size: int
    pages: int
