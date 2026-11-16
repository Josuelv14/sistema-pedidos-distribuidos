from decimal import Decimal, InvalidOperation
from threading import Lock


class BillingService:
    def __init__(self):
        self._sales = {}
        self._lock = Lock()

    def process_payment(self, order_id: str, total: str) -> dict:
        if not order_id.strip():
            raise ValueError("El ID del pedido es obligatorio")
        try:
            amount = Decimal(total)
        except InvalidOperation as exc:
            raise ValueError("El total debe ser un número válido") from exc
        if not amount.is_finite() or amount <= 0:
            raise ValueError("El total debe ser mayor que cero")
        try:
            rounded = amount.quantize(Decimal("0.01"))
        except InvalidOperation as exc:
            raise ValueError("El total excede el límite admitido") from exc
        if amount != rounded:
            raise ValueError("El total debe tener como máximo dos decimales")

        with self._lock:
            previous = self._sales.get(order_id)
            if previous is not None:
                if Decimal(previous["total"]) != amount:
                    raise ValueError("El pedido ya fue pagado con otro total")
                return dict(previous)
            sale = {
                "order_id": order_id,
                "approved": True,
                "invoice_id": f"FAC-{len(self._sales) + 1:06d}",
                "total": format(amount, ".2f"),
            }
            self._sales[order_id] = sale
            return dict(sale)

    def get_sales_summary(self) -> dict:
        with self._lock:
            revenue = sum(
                (Decimal(sale["total"]) for sale in self._sales.values()),
                Decimal("0.00"),
            )
            return {
                "sales_count": len(self._sales),
                "total_revenue": format(revenue, ".2f"),
            }
