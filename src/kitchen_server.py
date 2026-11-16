"""Servidor TCP basico para recibir pedidos de cocina.

Asistencia de IA: plantilla inicial; verificar y registrar en la bitacora.
"""

import json
import socketserver

HOST = "127.0.0.1"
PORT = 50052


class KitchenHandler(socketserver.StreamRequestHandler):
    def handle(self):
        self.request.settimeout(2)
        try:
            line = self.rfile.readline(4097)
            if not line.endswith(b"\n") or len(line) > 4096:
                answer = {"ok": False, "error": "Mensaje incompleto"}
            else:
                message = json.loads(line.decode("utf-8"))
                order = message.get("order") if isinstance(message, dict) else None
                if (not isinstance(order, dict) or
                        message.get("action") != "CREATE_ORDER" or
                        not isinstance(order.get("id"), str)):
                    answer = {"ok": False, "error": "Pedido invalido"}
                else:
                    print(f"Cocina recibio: {order['id']}", flush=True)
                    answer = {"ok": True, "order_id": order["id"]}
        except (json.JSONDecodeError, UnicodeDecodeError):
            answer = {"ok": False, "error": "JSON invalido"}
        except TimeoutError:
            answer = {"ok": False, "error": "Tiempo de espera agotado"}
        except (ConnectionResetError, OSError):
            return

        try:
            self.wfile.write((json.dumps(answer) + "\n").encode("utf-8"))
        except OSError:
            pass


class KitchenServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


def serve():
    with KitchenServer((HOST, PORT), KitchenHandler) as server:
        print(f"Cocina TCP escuchando en {HOST}:{PORT}", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("Cocina TCP detenida", flush=True)


if __name__ == "__main__":
    serve()
