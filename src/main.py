from typing import Annotated

import grpc
from fastapi import FastAPI, Header, HTTPException, status

from src.models import Order, OrderCreate, OrderStatus, OrderStatusUpdate
from src.services.billing_client import BillingClient
from src.services.orders import IdempotencyConflictError, OrdersService
from src.services.kitchen_client import (
    KitchenClient, KitchenProtocolError, KitchenRejectedError, KitchenUnavailableError,
)

app = FastAPI(title="Sistema de pedidos", version="1.0.0")
orders_service = OrdersService()
billing_client = BillingClient()
kitchen_client = KitchenClient()  # Integracion TCP asistida por IA; ver bitacora.

def dispatch_to_kitchen(order: Order) -> Order:
    """Despacha pedidos pagados; cocina deduplica por el ID de pedido."""
    if order.status not in (OrderStatus.PAID, OrderStatus.PREPARING):
        return order
    try:
        response = kitchen_client.send_order(order)
    except KitchenUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "message": "El pago se registro, pero cocina no responde. Reintente el despacho.",
                "order_id": order.id,
                "status": order.status.value,
            },
        ) from exc
    except (KitchenRejectedError, KitchenProtocolError) as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"message": f"Cocina rechazo el despacho: {exc}", "order_id": order.id},
        ) from exc
    return orders_service.update_status(order.id, OrderStatus(response["status"]))


def pay_order(order: Order) -> Order:
    if order.status == OrderStatus.PENDING:
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
        # Se conserva PAID aunque cocina no responda.
        order = orders_service.update_status(order.id, OrderStatus.PAID)
    return dispatch_to_kitchen(order)

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


@app.post("/orders/{order_id}/dispatch", response_model=Order)
def retry_kitchen_dispatch(order_id: str) -> Order:
    order = orders_service.get_order(order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    if order.status == OrderStatus.PENDING:
        raise HTTPException(status_code=409, detail="El pedido aun no ha sido pagado")
    return dispatch_to_kitchen(order)


@app.post("/orders/{order_id}/ready", response_model=Order)
def mark_order_ready(order_id: str) -> Order:
    """Accion simulada del personal de cocina al terminar la preparacion."""
    order = orders_service.get_order(order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    if order.status == OrderStatus.READY:
        return order
    if order.status != OrderStatus.PREPARING:
        raise HTTPException(status_code=409, detail="El pedido no esta en preparacion")
    try:
        kitchen_client.mark_ready(order.id)
    except KitchenUnavailableError as exc:
        raise HTTPException(status_code=503, detail="Cocina no responde") from exc
    except (KitchenRejectedError, KitchenProtocolError) as exc:
        raise HTTPException(status_code=502, detail=f"No se pudo marcar listo: {exc}") from exc
    return orders_service.update_status(order.id, OrderStatus.READY)


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
