import os
import time
from concurrent import futures

import grpc

import inventory_pb2
import inventory_pb2_grpc


INVENTORY = {"book": 10, "pen": 25, "laptop": 3}
DELAY_MS = int(os.getenv("INVENTORY_DELAY_MS", "0"))


class InventoryService(inventory_pb2_grpc.InventoryServiceServicer):
    def CheckInventory(self, request, context):
        if not request.item_id.strip():
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "item_id must not be empty")
        if request.quantity <= 0:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "quantity must be positive")

        if DELAY_MS > 0:
            time.sleep(DELAY_MS / 1000)

        if request.item_id not in INVENTORY:
            context.abort(grpc.StatusCode.NOT_FOUND, "item was not found")

        remaining = INVENTORY[request.item_id]
        if request.quantity > remaining:
            context.abort(
                grpc.StatusCode.FAILED_PRECONDITION,
                f"only {remaining} unit(s) available",
            )

        return inventory_pb2.InventoryResponse(
            item_id=request.item_id,
            quantity_requested=request.quantity,
            quantity_remaining=remaining - request.quantity,
            available=True,
        )


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    inventory_pb2_grpc.add_InventoryServiceServicer_to_server(InventoryService(), server)
    server.add_insecure_port("127.0.0.1:5003")
    server.start()
    print(f"gRPC Inventory Service listening on localhost:5003 (delay={DELAY_MS}ms)")
    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        server.stop(0)


if __name__ == "__main__":
    serve()
