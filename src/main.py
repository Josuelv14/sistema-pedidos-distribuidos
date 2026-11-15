from typing import Annotated

import grpc
from fastapi import FastAPI, Header, HTTPException, status

from src.models import Order, OrderCreate, OrderStatus, OrderStatusUpdate
from src.services.billing_client import BillingClient
from src.services.orders import IdempotencyConflictError, OrdersService

app = FastAPI(title="Sistema de pedidos", version="1.0.0")
orders_service = OrdersService()
billing_client = BillingClient()


def pay_order(order: Order) -> Order:
    if order.status != OrderStatus.PENDING:
        return order
    try:
        payment = billing_client.process_payment(order.id, format(order.total, ".2f"))
    except grpc.RpcError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "message": "No se pudo confirmar el pago con caja. Reintente el pago.",
                "order_id": order.id,
            },
        ) from exc
    if not payment.approved:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Pago no aprobado",
        )
    return orders_service.update_status(order.id, OrderStatus.PAID)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/orders/", response_model=Order, status_code=status.HTTP_201_CREATED)
def create_order(
    order_data: OrderCreate,
    idempotency_key: Annotated[
        str, Header(alias="X-Idempotency-Key", min_length=1, max_length=255)
    ],
) -> Order:
    key = idempotency_key.strip()
    if not key:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="X-Idempotency-Key no puede estar vacío",
        )
    try:
        order = orders_service.create_order(order_data, key)
    except IdempotencyConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="La clave de idempotencia ya se utilizó con otro contenido",
        ) from exc
    return pay_order(order)


@app.post("/orders/{order_id}/pay", response_model=Order)
def retry_payment(order_id: str) -> Order:
    order = orders_service.get_order(order_id)
    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Pedido no encontrado"
        )
    return pay_order(order)


@app.get("/orders/", response_model=list[Order])
def list_orders() -> list[Order]:
    return orders_service.list_orders()


@app.get("/orders/{order_id}", response_model=Order)
def get_order(order_id: str) -> Order:
    order = orders_service.get_order(order_id)
    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Pedido no encontrado"
        )
    return order


@app.patch("/orders/{order_id}/status", response_model=Order)
def update_order_status(order_id: str, update: OrderStatusUpdate) -> Order:
    order = orders_service.update_status(order_id, update.status)
    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Pedido no encontrado"
        )
    return order
