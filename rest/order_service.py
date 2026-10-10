import requests
from flask import Flask, jsonify, request


app = Flask(__name__)
INVENTORY_URL = "http://127.0.0.1:5001/inventory/check"
INVENTORY_TIMEOUT_SECONDS = 1.0


@app.post("/orders")
def create_order():
    payload = request.get_json(silent=True) or {}

    try:
        inventory_response = requests.post(
            INVENTORY_URL,
            json=payload,
            timeout=INVENTORY_TIMEOUT_SECONDS,
        )
    except requests.Timeout:
        return jsonify(
            error="inventory_timeout",
            message="Inventory Service exceeded the 1.0 second timeout",
            order_status="not_processed",
        ), 504
    except requests.RequestException as exc:
        app.logger.warning("Inventory Service request failed: %s", exc)
        return jsonify(
            error="inventory_unavailable",
            message="Inventory Service could not be reached",
            order_status="not_processed",
        ), 503

    if not inventory_response.ok:
        body = inventory_response.json()
        return jsonify(
            error=body.get("error", "inventory_rejected"),
            message="Order could not be accepted by Inventory Service",
            order_status="rejected",
            inventory=body,
        ), inventory_response.status_code

    inventory = inventory_response.json()
    return jsonify(
        order_status="accepted",
        item_id=payload["item_id"],
        quantity=payload["quantity"],
        inventory=inventory,
    ), 200


if __name__ == "__main__":
    print("REST Order Service listening on http://localhost:5000")
    app.run(host="127.0.0.1", port=5000)
