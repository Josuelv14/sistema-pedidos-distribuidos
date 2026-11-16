"""Cliente del protocolo JSON/TCP de cocina.

Codigo asistido por IA: registrar su uso en la bitacora del proyecto.
"""

import json
import socket

MAX_MESSAGE = 4096


class KitchenUnavailableError(Exception):
    """No es posible establecer comunicacion con cocina."""


class KitchenProtocolError(Exception):
    """La respuesta de cocina esta mal formada o es demasiado larga."""


class KitchenRejectedError(Exception):
    """Cocina rechazo una operacion valida a nivel de transporte."""

    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


class KitchenClient:
    def __init__(self, address=("127.0.0.1", 50052), timeout=2.0):
        self.address = address
        self.timeout = timeout

    def request(self, payload: dict) -> dict:
        outgoing = (json.dumps(payload, ensure_ascii=False) + "\n").encode("utf-8")
        if len(outgoing) > MAX_MESSAGE:
            raise KitchenProtocolError("Solicitud TCP demasiado larga")

        try:
            with socket.create_connection(self.address, timeout=self.timeout) as sock:
                sock.settimeout(self.timeout)
                sock.sendall(outgoing)
                with sock.makefile("rb") as reader:
                    incoming = reader.readline(MAX_MESSAGE + 1)
        except OSError as exc:
            raise KitchenUnavailableError("Cocina TCP no responde") from exc

        if not incoming.endswith(b"\n") or len(incoming) > MAX_MESSAGE:
            raise KitchenProtocolError("Respuesta TCP incompleta o excesiva")
        try:
            answer = json.loads(incoming.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise KitchenProtocolError("Respuesta TCP no es JSON") from exc
        if not isinstance(answer, dict) or not isinstance(answer.get("ok"), bool):
            raise KitchenProtocolError("Respuesta TCP sin campo 'ok' valido")
        if not answer["ok"]:
            raise KitchenRejectedError(str(answer.get("code", "ERROR")),
                                       str(answer.get("error", "Operacion rechazada")))
        if (not isinstance(answer.get("order_id"), str)
                or answer.get("status") not in ("PREPARING", "READY")):
            raise KitchenProtocolError("Respuesta TCP sin ID o estado valido")
        return answer

    def send_order(self, order) -> dict:
        return self.request({
            "action": "CREATE_ORDER",
            "order": {"id": order.id, "product": order.product,
                      "quantity": order.quantity},
        })

    def mark_ready(self, order_id: str) -> dict:
        return self.request({"action": "READY_ORDER", "order_id": order_id})

    def get_order(self, order_id: str) -> dict:
        return self.request({"action": "GET_ORDER", "order_id": order_id})
