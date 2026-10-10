from concurrent import futures

import grpc
from flask import Flask, jsonify, request

import inventory_pb2
import inventory_pb2_grpc


app = Flask(__name__)
INVENTORY_TARGET = "127.0.0.1:5003"
INVENTORY_DEADLINE_SECONDS = 1.0


@app.post("/orders")
def create_order():
    payload = request.get_json(silent=True) or {}
    item_id = payload.get("item_id")
    quantity = payload.get("quantity")

    try:
        quantity = int(quantity)
    except (TypeError, ValueError):
        return jsonify(error="quantity must be a positive integer"), 400

    if not isinstance(item_id, str) or not item_id.strip() or quantity <= 0:
        return jsonify(error="item_id and a positive quantity are required"), 400

    try:
        with grpc.insecure_channel(INVENTORY_TARGET) as channel:
            stub = inventory_pb2_grpc.InventoryServiceStub(channel)
            inventory = stub.CheckInventory(
                inventory_pb2.InventoryRequest(item_id=item_id, quantity=quantity),
                timeout=INVENTORY_DEADLINE_SECONDS,
            )
    except grpc.RpcError as exc:
        code = exc.code()
        if code == grpc.StatusCode.DEADLINE_EXCEEDED:
            return jsonify(
                error="inventory_deadline_exceeded",
                message="Inventory Service exceeded the 1.0 second gRPC deadline",
                order_status="not_processed",
            ), 504
        if code == grpc.StatusCode.FAILED_PRECONDITION:
            return jsonify(
                error="insufficient_inventory",
                message=exc.details(),
                order_status="rejected",
            ), 409
        if code == grpc.StatusCode.NOT_FOUND:
            return jsonify(
                error="item_not_found",
                message=exc.details(),
                order_status="rejected",
            ), 404
        if code == grpc.StatusCode.INVALID_ARGUMENT:
            return jsonify(error="invalid_inventory_request", message=exc.details()), 400
        return jsonify(
            error="inventory_unavailable",
            message=exc.details() or "Inventory Service could not be reached",
            order_status="not_processed",
        ), 503

    return jsonify(
        order_status="accepted",
        item_id=item_id,
        quantity=quantity,
        inventory={
            "available": inventory.available,
            "item_id": inventory.item_id,
            "quantity_requested": inventory.quantity_requested,
            "quantity_remaining": inventory.quantity_remaining,
        },
    ), 200


if __name__ == "__main__":
    print("gRPC Order Service listening on http://localhost:5002")
    app.run(host="127.0.0.1", port=5002)
