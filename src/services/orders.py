import hashlib
import json
import secrets
import string
from decimal import Decimal
from threading import Lock

from src.models import Order, OrderCreate, OrderStatus


class IdempotencyConflictError(Exception):
    """Raised when an idempotency key is reused for a different request."""


class OrdersService:
    def __init__(self) -> None:
        self._orders: dict[str, Order] = {}
        self._idempotency_keys: dict[str, tuple[str, str]] = {}
        self._lock = Lock()

    def create_order(self, order_data: OrderCreate, idempotency_key: str) -> Order:
        canonical_request = {
            "product": order_data.product,
            "quantity": order_data.quantity,
            "unit_price": format(order_data.unit_price, ".2f"),
        }
        payload = json.dumps(canonical_request, sort_keys=True, separators=(",", ":"))
        fingerprint = hashlib.sha256(payload.encode("utf-8")).hexdigest()

        with self._lock:
            previous = self._idempotency_keys.get(idempotency_key)
            if previous is not None:
                previous_fingerprint, order_id = previous
                if previous_fingerprint != fingerprint:
                    raise IdempotencyConflictError
                return self._orders[order_id]

            order_id = self._new_id()
            order = Order(
                id=order_id,
                total=Decimal(order_data.quantity) * order_data.unit_price,
                **order_data.model_dump(),
            )
            self._orders[order.id] = order
            self._idempotency_keys[idempotency_key] = (fingerprint, order.id)
            return order

    def list_orders(self) -> list[Order]:
        with self._lock:
            return list(self._orders.values())

    def get_order(self, order_id: str) -> Order | None:
        with self._lock:
            return self._orders.get(order_id)

    def update_status(self, order_id: str, new_status: OrderStatus) -> Order | None:
        with self._lock:
            order = self._orders.get(order_id)
            if order is None:
                return None
            updated_order = order.model_copy(update={"status": new_status})
            self._orders[order_id] = updated_order
            return updated_order

    def _new_id(self) -> str:
        alphabet = string.ascii_letters + string.digits
        while True:
            order_id = "".join(secrets.choice(alphabet) for _ in range(8))
            if order_id not in self._orders:
                return order_id
