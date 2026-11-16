import unittest
from concurrent import futures
from unittest.mock import patch

import grpc
from fastapi import HTTPException

from src import main
from src.billing_server import BillingServicer
from src.models import OrderCreate, OrderStatus
from src.proto import billing_pb2, billing_pb2_grpc
from src.services import orders
from src.services.billing_client import BillingClient
from src.services.orders import OrdersService


class BillingTests(unittest.TestCase):
    def setUp(self):
        self.servicer = BillingServicer()
        self.server = grpc.server(futures.ThreadPoolExecutor(max_workers=2))
        billing_pb2_grpc.add_BillingServiceServicer_to_server(
            self.servicer, self.server
        )
        port = self.server.add_insecure_port("127.0.0.1:0")
        self.server.start()
        self.channel = grpc.insecure_channel(f"127.0.0.1:{port}")
        self.stub = billing_pb2_grpc.BillingServiceStub(self.channel)
        self.client = BillingClient(f"127.0.0.1:{port}", timeout=0.5)

    def tearDown(self):
        self.channel.close()
        self.server.stop(0).wait()

    def summary(self):
        return self.stub.GetSalesSummary(
            billing_pb2.SalesSummaryRequest(), timeout=2
        )

    def test_payment_and_sales_summary(self):
        payment = self.client.process_payment("ABC12345", "7.00")
        self.assertTrue(payment.approved)
        self.assertEqual(payment.order_id, "ABC12345")
        self.assertEqual(payment.invoice_id, "FAC-000001")
        self.assertEqual(payment.total, "7.00")
        self.client.process_payment("DEF12345", "3.50")
        summary = self.summary()
        self.assertEqual(summary.sales_count, 2)
        self.assertEqual(summary.total_revenue, "10.50")

    def test_repeated_payment_does_not_duplicate_sale(self):
        first = self.client.process_payment("ABC12345", "7.00")
        second = self.client.process_payment("ABC12345", "7.00")
        self.assertEqual(first, second)
        self.assertEqual(self.summary().sales_count, 1)

    def test_repeated_payment_with_different_total_is_rejected(self):
        self.client.process_payment("ABC12345", "7.00")
        with self.assertRaises(grpc.RpcError) as result:
            self.client.process_payment("ABC12345", "8.00")
        self.assertEqual(result.exception.code(), grpc.StatusCode.INVALID_ARGUMENT)
        self.assertEqual(self.summary().total_revenue, "7.00")

    def test_invalid_payment_is_rejected(self):
        for total in ["-1", "0", "NaN", "1.001", "invalid"]:
            with self.subTest(total=total):
                with self.assertRaises(grpc.RpcError) as result:
                    self.client.process_payment("ABC12345", total)
                self.assertEqual(
                    result.exception.code(), grpc.StatusCode.INVALID_ARGUMENT
                )
        self.assertEqual(self.summary().sales_count, 0)

    def test_orders_use_grpc_and_become_paid(self):
        orders = OrdersService()
        data = OrderCreate(product="Cafe", quantity=2, unit_price="3.50")

        with patch.object(main, "orders_service", orders), \
            patch.object(main, "billing_client", self.client), \
            patch.object(main, "dispatch_to_kitchen", side_effect=lambda order: order):

            first = main.create_order(data, "pedido-1")
            second = main.create_order(data, "pedido-1")

            self.assertEqual(first.status, OrderStatus.PAID)
            self.assertEqual(first.id, second.id)
            self.assertEqual(self.summary().sales_count, 1)

    def test_unavailable_billing_keeps_order_pending_and_allows_retry(self):
        orders = OrdersService()
        data = OrderCreate(product="Cafe", quantity=2, unit_price="3.50")
        self.server.stop(0).wait()
        with patch.object(main, "orders_service", orders), \
            patch.object(main, "billing_client", self.client), \
            patch.object(main, "dispatch_to_kitchen", side_effect=lambda order: order):
            with self.assertRaises(HTTPException) as result:
                main.create_order(data, "pedido-1")
            self.assertEqual(result.exception.status_code, 503)
            order_id = result.exception.detail["order_id"]
            self.assertEqual(orders.get_order(order_id).status, OrderStatus.PENDING)
            with self.assertRaises(grpc.RpcError) as rpc_result:
                self.client.process_payment(order_id, "7.00")
            self.assertIn(
                rpc_result.exception.code(),
                [grpc.StatusCode.UNAVAILABLE, grpc.StatusCode.DEADLINE_EXCEEDED],
            )

            recovery_server = grpc.server(
                futures.ThreadPoolExecutor(max_workers=2)
            )
            billing_pb2_grpc.add_BillingServiceServicer_to_server(
                self.servicer, recovery_server
            )
            port = recovery_server.add_insecure_port("127.0.0.1:0")
            recovery_server.start()
            try:
                with patch.object(
                    main, "billing_client", BillingClient(f"127.0.0.1:{port}")
                ):
                    paid = main.retry_payment(order_id)
                    self.assertEqual(paid.status, OrderStatus.PAID)
                    main.retry_payment(order_id)
                self.assertEqual(
                    self.servicer.service.get_sales_summary()["sales_count"], 1
                )
            finally:
                recovery_server.stop(0).wait()


if __name__ == "__main__":
    unittest.main()
