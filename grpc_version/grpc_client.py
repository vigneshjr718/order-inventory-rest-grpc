import sys

import grpc

import inventory_pb2
import inventory_pb2_grpc


def main():
    if len(sys.argv) != 3:
        raise SystemExit("Usage: python grpc_version/grpc_client.py <item_id> <quantity>")

    item_id = sys.argv[1]
    quantity = int(sys.argv[2])

    with grpc.insecure_channel("127.0.0.1:5003") as channel:
        stub = inventory_pb2_grpc.InventoryServiceStub(channel)
        response = stub.CheckInventory(
            inventory_pb2.InventoryRequest(item_id=item_id, quantity=quantity),
            timeout=1.0,
        )
        print(response)


if __name__ == "__main__":
    try:
        main()
    except grpc.RpcError as exc:
        print(f"gRPC error: code={exc.code().name} details={exc.details()}")
        raise SystemExit(1)
