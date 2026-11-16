"""Microservicio de cocina basado en sockets TCP.

Protocolo: un mensaje JSON por linea (maximo 4096 bytes) y una respuesta JSON.
Los datos estan en memoria.
"""

import json
import re
import socketserver
from threading import Lock

HOST = "127.0.0.1"
PORT = 50052
MAX_MESSAGE = 4096
ORDER_ID_PATTERN = re.compile(r"^[A-Za-z0-9]{8}$")


def failure(code: str, message: str) -> dict:
    return {"ok": False, "code": code, "error": message}


class KitchenServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True
    block_on_close = False

    def __init__(self, server_address, RequestHandlerClass):
        self.orders: dict[str, dict] = {}
        self.orders_lock = Lock()
        super().__init__(server_address, RequestHandlerClass)

    def process_message(self, message: object) -> dict:
        if not isinstance(message, dict):
            return failure("BAD_REQUEST", "El mensaje debe ser un objeto JSON")
        action = message.get("action")

        if action == "CREATE_ORDER":
            order = message.get("order")
            if not isinstance(order, dict):
                return failure("BAD_REQUEST", "Falta el objeto order")
            order_id = order.get("id")
            product = order.get("product")
            quantity = order.get("quantity")
            if (not isinstance(order_id, str)
                    or not ORDER_ID_PATTERN.fullmatch(order_id)
                    or not isinstance(product, str)
                    or not 1 <= len(product.strip()) <= 200
                    or type(quantity) is not int or quantity < 1):
                return failure("BAD_REQUEST", "Datos del pedido invalidos")
            with self.orders_lock:
                previous = self.orders.get(order_id)
                if previous is not None:
                    if (previous["product"] != product
                            or previous["quantity"] != quantity):
                        return failure("CONFLICT", "El ID ya pertenece a otro pedido")
                    return {
                        "ok": True, "order_id": order_id,
                        "status": previous["status"], "duplicate": True,
                    }
                self.orders[order_id] = {
                    "id": order_id, "product": product,
                    "quantity": quantity, "status": "PREPARING",
                }
                print(f"[COCINA] Preparando {order_id}: {quantity} x {product}", flush=True)
            return {"ok": True, "order_id": order_id,
                    "status": "PREPARING", "duplicate": False}

        if action in ("READY_ORDER", "GET_ORDER"):
            order_id = message.get("order_id")
            if not isinstance(order_id, str) or not ORDER_ID_PATTERN.fullmatch(order_id):
                return failure("BAD_REQUEST", "ID del pedido invalido")
            with self.orders_lock:
                order = self.orders.get(order_id)
                if order is None:
                    return failure("NOT_FOUND", "Pedido no encontrado en cocina")
                if action == "READY_ORDER":
                    if order["status"] != "READY":
                        order["status"] = "READY"
                        print(f"[COCINA] Pedido listo: {order_id}", flush=True)
                return {"ok": True, "order_id": order_id,
                        "status": order["status"],
                        "product": order["product"], "quantity": order["quantity"]}

        return failure("BAD_REQUEST", "Accion TCP desconocida")


class KitchenHandler(socketserver.StreamRequestHandler):
    def handle(self):
        self.request.settimeout(2)
        try:
            line = self.rfile.readline(MAX_MESSAGE + 1)
            if (not line or not line.endswith(b"\n")
                    or len(line) > MAX_MESSAGE):
                response = failure("BAD_REQUEST", "Mensaje incompleto o demasiado largo")
            else:
                message = json.loads(line.decode("utf-8"))
                response = self.server.process_message(message)
        except (json.JSONDecodeError, UnicodeDecodeError):
            response = failure("BAD_REQUEST", "JSON invalido")
        except TimeoutError:
            response = failure("TIMEOUT", "Cliente sin respuesta")
        except OSError:
            # Un cliente puede cerrarse sin terminar de enviar el mensaje.
            return

        try:
            self.wfile.write((json.dumps(response, ensure_ascii=False) + "\n").encode("utf-8"))
        except OSError:
            # La desconexion de un cliente no detiene el servidor.
            pass


def serve():
    with KitchenServer((HOST, PORT), KitchenHandler) as server:
        print(f"Cocina TCP escuchando en {HOST}:{PORT}", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("Cocina TCP detenida", flush=True)


if __name__ == "__main__":
    serve()
