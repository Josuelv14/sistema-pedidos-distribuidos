"""Pruebas de TCP de cocina y la integracion API.

Pruebas elaboradas con asistencia de IA. Ejecutar y documentar resultados reales.
"""

import asyncio
import json
import socket
import threading
import unittest
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import HTTPException

from src.kitchen_server import KitchenHandler, KitchenServer
from src.models import OrderCreate, OrderStatus
from src.services.kitchen_client import (
    KitchenClient, KitchenRejectedError, KitchenUnavailableError,
)
from src.services.orders import OrdersService


def sample_order(order_id="TST00001", product="Cafe", quantity=2):
    return SimpleNamespace(id=order_id, product=product, quantity=quantity)


class KitchenTcpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = KitchenServer(("127.0.0.1", 0), KitchenHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.address = cls.server.server_address

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def setUp(self):
        self.client = KitchenClient(self.address, timeout=0.8)

    def test_01_crear_y_marcar_listo(self):
        first = self.client.send_order(sample_order("TST00001"))
        self.assertEqual(first["status"], "PREPARING")
        self.assertFalse(first["duplicate"])
        finished = self.client.mark_ready("TST00001")
        self.assertEqual(finished["status"], "READY")

    def test_02_reintento_no_duplica(self):
        first = self.client.send_order(sample_order("TST00002"))
        second = self.client.send_order(sample_order("TST00002"))
        self.assertFalse(first["duplicate"])
        self.assertTrue(second["duplicate"])
        self.assertEqual(len([k for k in self.server.orders if k == "TST00002"]), 1)

    def test_03_conflicto_mismo_id(self):
        self.client.send_order(sample_order("TST00003"))
        with self.assertRaises(KitchenRejectedError) as caught:
            self.client.send_order(sample_order("TST00003", product="Sandwich"))
        self.assertEqual(caught.exception.code, "CONFLICT")

    def test_04_json_invalido(self):
        with socket.create_connection(self.address, timeout=1) as sock:
            sock.sendall(b"{invalido}\n")
            with sock.makefile("rb") as reader:
                result = json.loads(reader.readline())
        self.assertFalse(result["ok"])
        self.assertEqual(result["code"], "BAD_REQUEST")

    def test_05_desconexion_no_detiene_el_servicio(self):
        with socket.create_connection(self.address, timeout=1) as sock:
            sock.sendall(b'{"action":"CREATE_ORDER"')
            # El cierre no envia un mensaje terminado en salto de linea.
        reply = self.client.send_order(sample_order("TST00005"))
        self.assertTrue(reply["ok"])

    def test_06_servidor_no_disponible(self):
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            port = probe.getsockname()[1]
        unavailable = KitchenClient(("127.0.0.1", port), timeout=0.3)
        with self.assertRaises(KitchenUnavailableError):
            unavailable.send_order(sample_order("TST00006"))

    def test_07_consulta_pedido_inexistente(self):
        with self.assertRaises(KitchenRejectedError) as caught:
            self.client.get_order("ZZZ99999")
        self.assertEqual(caught.exception.code, "NOT_FOUND")


class KitchenApiIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = KitchenServer(("127.0.0.1", 0), KitchenHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def setUp(self):
        from src import main as api
        self.api = api
        self.old_orders_service = api.orders_service
        self.old_kitchen_client = api.kitchen_client
        api.orders_service = OrdersService()
        api.kitchen_client = KitchenClient(self.server.server_address, timeout=0.8)
        self.payment_patch = patch.object(
            api.billing_client, "process_payment", return_value=SimpleNamespace(approved=True),
        )
        self.payment_mock = self.payment_patch.start()

    def tearDown(self):
        self.payment_patch.stop()
        self.api.orders_service = self.old_orders_service
        self.api.kitchen_client = self.old_kitchen_client

    def test_08_flujo_api_pago_tcp_listo(self):
        request = OrderCreate(product="Jugo", quantity=1, unit_price=Decimal("2.50"))
        created = self.api.create_order(request, "key-test-08")
        self.assertEqual(created.status, OrderStatus.PREPARING)
        self.assertEqual(self.payment_mock.call_count, 1)
        same = self.api.create_order(request, "key-test-08")
        self.assertEqual(same.id, created.id)
        self.assertEqual(self.payment_mock.call_count, 1)
        completed = asyncio.run(self.api.mark_order_ready(created.id))
        self.assertEqual(completed.status, OrderStatus.READY)

    def test_09_fallo_cocina_conserva_pago_y_permita_reintento(self):
        real_client = self.api.kitchen_client
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            closed_port = probe.getsockname()[1]
        self.api.kitchen_client = KitchenClient(("127.0.0.1", closed_port), timeout=0.3)
        request = OrderCreate(product="Pan", quantity=1, unit_price=Decimal("1.00"))
        with self.assertRaises(HTTPException) as caught:
            self.api.create_order(request, "key-test-09")
        self.assertEqual(caught.exception.status_code, 503)
        order_id = caught.exception.detail["order_id"]
        self.assertEqual(self.api.orders_service.get_order(order_id).status, OrderStatus.PAID)
        self.api.kitchen_client = real_client
        dispatched = self.api.retry_kitchen_dispatch(order_id)
        self.assertEqual(dispatched.status, OrderStatus.PREPARING)
        self.assertEqual(self.payment_mock.call_count, 1)


if __name__ == "__main__":
    unittest.main()
