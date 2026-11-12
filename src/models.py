from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class OrderCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    product: str = Field(min_length=1, max_length=200)
    quantity: int = Field(gt=0)
    unit_price: Decimal = Field(gt=0, max_digits=10, decimal_places=2)


class OrderStatus(str, Enum):
    PENDING = "PENDING"
    PREPARING = "PREPARING"
    READY = "READY"
    PAID = "PAID"


class OrderStatusUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: OrderStatus


class Order(OrderCreate):
    id: str = Field(min_length=8, max_length=8, pattern=r"^[A-Za-z0-9]{8}$")
    total: Decimal
    status: OrderStatus = OrderStatus.PENDING
