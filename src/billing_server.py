from concurrent import futures

import grpc

from src.proto import billing_pb2, billing_pb2_grpc
from src.services.billing import BillingService


class BillingServicer(billing_pb2_grpc.BillingServiceServicer):
    def __init__(self):
        self.service = BillingService()

    def ProcessPayment(self, request, context):
        try:
            payment = self.service.process_payment(request.order_id, request.total)
        except ValueError as exc:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, str(exc))
        return billing_pb2.PaymentResponse(**payment)

    def GetSalesSummary(self, request, context):
        return billing_pb2.SalesSummaryResponse(**self.service.get_sales_summary())


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=4))
    billing_pb2_grpc.add_BillingServiceServicer_to_server(BillingServicer(), server)
    server.add_insecure_port("127.0.0.1:50051")
    server.start()
    print("Caja gRPC disponible en 127.0.0.1:50051")
    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        server.stop(0).wait()


if __name__ == "__main__":
    serve()
