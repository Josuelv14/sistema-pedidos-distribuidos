import grpc

from src.proto import billing_pb2, billing_pb2_grpc


class BillingClient:
    def __init__(self, address="127.0.0.1:50051", timeout=2):
        self.address = address
        self.timeout = timeout

    def process_payment(self, order_id: str, total: str):
        with grpc.insecure_channel(self.address) as channel:
            client = billing_pb2_grpc.BillingServiceStub(channel)
            return client.ProcessPayment(
                billing_pb2.PaymentRequest(order_id=order_id, total=total),
                timeout=self.timeout,
            )
