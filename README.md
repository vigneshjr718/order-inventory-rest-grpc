# REST and gRPC Order–Inventory Services

This project implements the same Order → Inventory interaction in two ways:

- REST/HTTP using JSON and an HTTP client timeout
- gRPC using a `.proto` contract and a client deadline

The Order Service remains available when the Inventory Service responds too slowly. A temporary delay can be enabled with the `INVENTORY_DELAY_MS` environment variable.

## Project Structure

```text
.
├── grpc_version/
│   ├── inventory.proto
│   ├── inventory_pb2.py
│   ├── inventory_pb2_grpc.py
│   ├── grpc_client.py
│   ├── inventory_service.py
│   └── order_service.py
├── rest/
│   ├── inventory_service.py
│   └── order_service.py
├── evidence/
│   ├── grpc-deadline.png
│   ├── grpc-delay.png
│   ├── grpc-success.png
│   ├── grpc-recovery.png
│   ├── rest-timeout.png
│   ├── rest-delay.png
│   ├── rest-success.png
│   ├── rest-recovery-start.png
│   └── rest-recovery.png
├── requirements.txt
└── README.md
```

The `__pycache__` folder and `.venv` folder are temporary local folders and should not be uploaded to GitHub.

## Requirements

- Python 3.10 or newer
- pip

## Installation

Create a virtual environment:

```powershell
python -m venv .venv
```

Activate it on Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Install the dependencies:

```powershell
python -m pip install -r requirements.txt
```

For Windows PowerShell, use `Invoke-RestMethod` or `curl.exe` for testing. PowerShell does not use the backslash (`\`) for multiline commands.

## REST Version

The REST version uses JSON over HTTP.

Open two PowerShell terminals from the repository root.

### Terminal 1: Start the REST Inventory Service

```powershell
$env:INVENTORY_DELAY_MS = "0"
python rest/inventory_service.py
```

The REST Inventory Service listens on:

```text
http://localhost:5001
```

### Terminal 2: Start the REST Order Service

```powershell
python rest/order_service.py
```

The REST Order Service listens on:

```text
http://localhost:5000
```

### Available Inventory

| Item | Quantity |
|---|---:|
| book | 10 |
| pen | 25 |
| laptop | 3 |

### Successful REST Request

Open a third PowerShell terminal:

```powershell
$body = @{
    item_id = "book"
    quantity = 2
} | ConvertTo-Json

Invoke-RestMethod `
    -Uri "http://localhost:5000/orders" `
    -Method Post `
    -ContentType "application/json" `
    -Body $body
```

Expected result:

```text
order_status : accepted
item_id      : book
quantity     : 2
```

The JSON response is:

```json
{
  "item_id": "book",
  "inventory": {
    "available": true,
    "item_id": "book",
    "quantity_requested": 2,
    "quantity_remaining": 8
  },
  "order_status": "accepted",
  "quantity": 2
}
```

The REST Order Service returns HTTP status `200 OK` for a successful request.

### REST Unavailable-Item Response

Request more inventory than is available:

```powershell
$body = @{
    item_id = "book"
    quantity = 20
} | ConvertTo-Json

Invoke-RestMethod `
    -Uri "http://localhost:5000/orders" `
    -Method Post `
    -ContentType "application/json" `
    -Body $body
```

Because the item exists but there is not enough inventory, the Order Service returns:

```text
HTTP 409 Conflict
```

### REST Timeout Demonstration

Stop the REST Inventory Service by pressing `Ctrl+C` in its terminal.

Restart it with a delay longer than the Order Service's one-second timeout:

```powershell
$env:INVENTORY_DELAY_MS = "2500"
python rest/inventory_service.py
```

Call the REST Order Service:

```powershell
$body = @{
    item_id = "book"
    quantity = 1
} | ConvertTo-Json

Invoke-RestMethod `
    -Uri "http://localhost:5000/orders" `
    -Method Post `
    -ContentType "application/json" `
    -Body $body
```

Expected result:

```text
inventory_timeout
Inventory Service exceeded the 1.0 second timeout
order_status: not_processed
```

The Order Service returns HTTP status:

```text
504 Gateway Timeout
```

The timeout is handled inside the request handler. The Order Service process continues running.

To restore normal operation, stop the delayed Inventory Service and restart it without a delay:

```powershell
$env:INVENTORY_DELAY_MS = "0"
python rest/inventory_service.py
```

Send another successful request. The successful response proves that the REST Order Service remained available after the timeout.

## gRPC Version

The gRPC contract is defined in:

```text
grpc_version/inventory.proto
```

The generated Python files are included:

```text
grpc_version/inventory_pb2.py
grpc_version/inventory_pb2_grpc.py
```

### Regenerating the gRPC Files

If `inventory.proto` changes, regenerate the Python files from the repository root:

```powershell
python -m grpc_tools.protoc -I grpc_version --python_out=grpc_version --grpc_python_out=grpc_version grpc_version/inventory.proto
```

### Terminal 1: Start the gRPC Inventory Service

```powershell
$env:INVENTORY_DELAY_MS = "0"
python grpc_version/inventory_service.py
```

The gRPC Inventory Service listens on:

```text
localhost:5003
```

### Terminal 2: Start the gRPC Order Service

```powershell
python grpc_version/order_service.py
```

The gRPC Order Service exposes an HTTP order endpoint at:

```text
http://localhost:5002/orders
```

The HTTP endpoint is used to submit an order. The Order Service communicates with the Inventory Service internally using gRPC.

The gRPC client uses a one-second deadline for the Inventory Service call.

### Successful gRPC Request

A direct gRPC request can be sent using the generated client:

```powershell
python grpc_version/grpc_client.py pen 4
```

Expected protobuf response:

```text
item_id: "pen"
quantity_requested: 4
quantity_remaining: 21
available: true
```

The gRPC-backed Order Service can also be tested using PowerShell:

```powershell
$body = @{
    item_id = "pen"
    quantity = 4
} | ConvertTo-Json

Invoke-RestMethod `
    -Uri "http://localhost:5002/orders" `
    -Method Post `
    -ContentType "application/json" `
    -Body $body
```

Expected result:

```text
order_status : accepted
item_id      : pen
quantity     : 4
```

The Order Service returns HTTP status `200 OK`.

### gRPC Unavailable-Item Response

Request more inventory than is available:

```powershell
$body = @{
    item_id = "laptop"
    quantity = 20
} | ConvertTo-Json

Invoke-RestMethod `
    -Uri "http://localhost:5002/orders" `
    -Method Post `
    -ContentType "application/json" `
    -Body $body
```

The Inventory Service returns the gRPC status:

```text
FAILED_PRECONDITION
```

The Order Service maps this to:

```text
HTTP 409 Conflict
```

Expected response:

```json
{
  "error": "insufficient_inventory",
  "order_status": "rejected"
}
```

### gRPC Deadline Demonstration

Stop the gRPC Inventory Service by pressing `Ctrl+C`.

Restart it with a delay longer than the one-second gRPC deadline:

```powershell
$env:INVENTORY_DELAY_MS = "2500"
python grpc_version/inventory_service.py
```

Run the direct gRPC client:

```powershell
python grpc_version/grpc_client.py pen 1
```

Expected result:

```text
gRPC error: code=DEADLINE_EXCEEDED
```

Call the gRPC-backed Order Service:

```powershell
$body = @{
    item_id = "pen"
    quantity = 1
} | ConvertTo-Json

Invoke-RestMethod `
    -Uri "http://localhost:5002/orders" `
    -Method Post `
    -ContentType "application/json" `
    -Body $body
```

Expected result:

```text
inventory_deadline_exceeded
Inventory Service exceeded the 1.0 second gRPC deadline
order_status: not_processed
```

The Order Service returns HTTP status:

```text
504 Gateway Timeout
```

The gRPC client catches `grpc.StatusCode.DEADLINE_EXCEEDED`. The Order Service continues running after the failure.

To restore normal operation, stop the delayed Inventory Service and restart it without a delay:

```powershell
$env:INVENTORY_DELAY_MS = "0"
python grpc_version/inventory_service.py
```

Send another successful request. The successful response proves that the gRPC Order Service remained available after the deadline failure.

## Evidence

The `evidence` folder contains nine screenshots showing successful requests, temporary delays, timeout/deadline failures, and service recovery.

### REST Evidence

![REST successful request](https://github.com/vigneshjr718/order-inventory-rest-grpc/blob/main/evidence/successful%20REST%20request.jpeg)

![REST Inventory Service delay](https://github.com/vigneshjr718/order-inventory-rest-grpc/blob/main/evidence/REST%20Inventory%20Service%20running%20with%20delay%3D3000ms.jpeg)

![REST timeout](https://github.com/vigneshjr718/order-inventory-rest-grpc/blob/main/evidence/REST%20timeout%20response.jpeg)

![REST Inventory Service restarted](https://github.com/vigneshjr718/order-inventory-rest-grpc/blob/main/evidence/REST%20Inventory%20Service%20restarted%20with%20delay%3D0ms.jpeg)

![REST recovery](https://github.com/vigneshjr718/order-inventory-rest-grpc/blob/main/evidence/successful%20REST%20request%20after%20recovery.jpegg)

### gRPC Evidence

![gRPC deadline exceeded](https://github.com/vigneshjr718/order-inventory-rest-grpc/blob/main/evidence/gRPC%20deadline%20exceeded.jpeg)

![gRPC Inventory Service delay](https://github.com/vigneshjr718/order-inventory-rest-grpc/blob/main/evidence/gRPC%20Inventory%20Service%20running%20with%20delay%3D3000ms.jpeg)

![gRPC Inventory Service restarted](https://github.com/vigneshjr718/order-inventory-rest-grpc/blob/main/evidence/gRPC%20Inventory%20Service%20restarted%20with%20delay%3D0ms.jpeg)

![gRPC successful request](https://github.com/vigneshjr718/order-inventory-rest-grpc/blob/main/evidence/successful%20gRPC%20request%20after%20recovery.jpeg)

## REST vs. gRPC Comparison

REST was straightforward to test because requests and responses were visible JSON sent through familiar HTTP endpoints. gRPC required defining the contract in a `.proto` file and generating client and server code, but it provided strongly typed messages and standard status codes. REST handled the slow dependency with an HTTP timeout, while gRPC used a deadline and reported `DEADLINE_EXCEEDED`. The two implementations used different error representations, but both returned a clear failure to the caller and kept the Order Service running. gRPC involved more setup, while REST was easier to inspect manually with PowerShell or curl.

## Conclusion

This project demonstrates the same Order → Inventory service interaction using both REST and gRPC. Both implementations validate inventory availability, handle unavailable items, enforce a client-side time limit, and continue running when the Inventory Service responds too slowly.
