import os
import time

from flask import Flask, jsonify, request


app = Flask(__name__)

INVENTORY = {"book": 10, "pen": 25, "laptop": 3}
DELAY_MS = int(os.getenv("INVENTORY_DELAY_MS", "0"))


@app.post("/inventory/check")
def check_inventory():
    payload = request.get_json(silent=True) or {}
    item_id = payload.get("item_id")
    quantity = payload.get("quantity")

    if not isinstance(item_id, str) or not item_id.strip():
        return jsonify(error="item_id must be a non-empty string"), 400
    if not isinstance(quantity, int) or isinstance(quantity, bool) or quantity <= 0:
        return jsonify(error="quantity must be a positive integer"), 400

    if DELAY_MS > 0:
        time.sleep(DELAY_MS / 1000)

    if item_id not in INVENTORY:
        return jsonify(error="item_not_found", item_id=item_id), 404

    remaining = INVENTORY[item_id]
    if quantity > remaining:
        return jsonify(
            error="insufficient_inventory",
            item_id=item_id,
            quantity_requested=quantity,
            quantity_available=remaining,
        ), 409

    return jsonify(
        available=True,
        item_id=item_id,
        quantity_requested=quantity,
        quantity_remaining=remaining - quantity,
    ), 200


if __name__ == "__main__":
    print(f"REST Inventory Service listening on http://localhost:5001 (delay={DELAY_MS}ms)")
    app.run(host="127.0.0.1", port=5001)
