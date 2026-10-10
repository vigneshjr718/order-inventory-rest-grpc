# REST and gRPC Order–Inventory Services

This project implements the same **Order → Inventory** interaction in two ways:

1. REST/HTTP with JSON and an HTTP client timeout.
2. gRPC with a `.proto` contract and a client deadline.

The Order Service remains available after the Inventory Service is too slow. A temporary delay can be enabled with the `INVENTORY_DELAY_MS` environment variable.

## Project structure

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
│   ├── grpc-deadline.txt
│   ├── grpc-success.txt
│   ├── order-stays-running.txt
│   ├── rest-success.txt
│   └── rest-timeout.txt
├── requirements.txt
└── README.md
```

## Requirements

- Python 3.10+
- pip

Install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate       # Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## REST version

Open two terminals from the repository root.

### Terminal 1: Inventory Service

```bash
INVENTORY_DELAY_MS=0 python rest/inventory_service.py
```

Windows PowerShell:

```powershell
$env:INVENTORY_DELAY_MS = "0"
python rest/inventory_service.py
```

The REST Inventory Service listens on `http://localhost:5001`.

### Terminal 2: Order Service

```bash
python rest/order_service.py
```

The REST Order Service listens on `http://localhost:5000`.

### Successful REST request and response

```bash
curl -i -X POST http://localhost:5000/orders \
  -H "Content-Type: application/json" \
  -d '{"item_id":"book","quantity":2}'
```

Expected response:

```http
HTTP/1.1 200 OK
Content-Type: application/json

{"item_id":"book","inventory":{"available":true,"item_id":"book","quantity_requested":2,"quantity_remaining":8},"order_status":"accepted","quantity":2}
```

Available inventory is:

| Item | Quantity |
|---|---:|
| `book` | 10 |
| `pen` | 25 |
| `laptop` | 3 |

### REST unavailable-item response

```bash
curl -i -X POST http://localhost:5000/orders \
  -H "Content-Type: application/json" \
  -d '{"item_id":"book","quantity":20}'
```

The Order Service returns HTTP `409 Conflict` because the item exists but there is not enough inventory.

### REST timeout demonstration

Stop the Inventory Service and restart it with a delay longer than the Order Service's one-second timeout:

```bash
INVENTORY_DELAY_MS=2500 python rest/inventory_service.py
```

Call the Order Service:

```bash
curl -i -X POST http://localhost:5000/orders \
  -H "Content-Type: application/json" \
  -d '{"item_id":"book","quantity":1}'
```

Expected response:

```http
HTTP/1.1 504 Gateway Timeout
Content-Type: application/json

{"error":"inventory_timeout","message":"Inventory Service exceeded the 1.0 second timeout","order_status":"not_processed"}
```

The timeout is handled inside the request handler, so the Order Service process continues running. A second request after restoring the Inventory Service should succeed.

## gRPC version

The gRPC contract is defined in [`grpc_version/inventory.proto`](grpc_version/inventory.proto). The generated Python files are included, so the service can be run immediately after installing the requirements.

Open two terminals from the repository root.

### Terminal 1: gRPC Inventory Service

```bash
INVENTORY_DELAY_MS=0 python grpc_version/inventory_service.py
```

Windows PowerShell:

```powershell
$env:INVENTORY_DELAY_MS = "0"
python grpc_version/inventory_service.py
```

The gRPC Inventory Service listens on `localhost:5003`.

### Terminal 2: gRPC Order Service

```bash
python grpc_version/order_service.py
```

The gRPC Order Service exposes an HTTP endpoint at `http://localhost:5002/orders`. It uses a gRPC client internally to call the Inventory Service with a one-second deadline.

### Successful gRPC request and response

The following command sends a direct gRPC request to the Inventory Service using the generated client stub:

```bash
python grpc_version/grpc_client.py pen 4
```

Expected protobuf response:

```text
item_id: "pen"
quantity_requested: 4
quantity_remaining: 21
available: true
```

The Order Service also exposes an HTTP submission endpoint so the result can be tested with `curl`. Its downstream call is gRPC:

```bash
curl -i -X POST http://localhost:5002/orders \
  -H "Content-Type: application/json" \
  -d '{"item_id":"pen","quantity":4}'
```

Expected response:

```http
HTTP/1.1 200 OK
Content-Type: application/json

{"item_id":"pen","inventory":{"available":true,"item_id":"pen","quantity_requested":4,"quantity_remaining":21},"order_status":"accepted","quantity":4}
```

The HTTP endpoint is only used to submit an order and display the result. The Order Service to Inventory Service call is gRPC.

### gRPC unavailable-item response

For an existing item with insufficient quantity, the gRPC Inventory Service returns `FAILED_PRECONDITION`, and the Order Service returns HTTP `409 Conflict`:

```bash
curl -i -X POST http://localhost:5002/orders \
  -H "Content-Type: application/json" \
  -d '{"item_id":"laptop","quantity":20}'
```

### gRPC deadline demonstration

Stop and restart the gRPC Inventory Service with a 2.5-second delay:

```bash
INVENTORY_DELAY_MS=2500 python grpc_version/inventory_service.py
```

The direct gRPC client now demonstrates the native gRPC status:

```bash
python grpc_version/grpc_client.py pen 1
```

Expected client output:

```text
gRPC error: code=DEADLINE_EXCEEDED details=Deadline Exceeded
```

Call the gRPC Order Service:

```bash
curl -i -X POST http://localhost:5002/orders \
  -H "Content-Type: application/json" \
  -d '{"item_id":"pen","quantity":1}'
```

Expected response:

```http
HTTP/1.1 504 Gateway Timeout
Content-Type: application/json

{"error":"inventory_deadline_exceeded","message":"Inventory Service exceeded the 1.0 second gRPC deadline","order_status":"not_processed"}
```

The gRPC client catches `grpc.StatusCode.DEADLINE_EXCEEDED`; the Order Service continues running and can process another request after the Inventory Service is responsive again.

## Evidence

The [`evidence/`](evidence) directory contains captured successful-call, timeout/deadline, and recovery outputs. To reproduce the evidence, follow the commands above. In a GitHub submission, screenshots of the same terminal results may also be added to this README.

- [REST success](evidence/rest-success.txt)
- [REST timeout](evidence/rest-timeout.txt)
- [gRPC success](evidence/grpc-success.txt)
- [gRPC deadline](evidence/grpc-deadline.txt)
- [Order Service recovery](evidence/order-stays-running.txt)

## REST vs. gRPC comparison

REST was straightforward to test because requests and responses were visible JSON sent through familiar HTTP endpoints. gRPC required defining the contract in a `.proto` file and generating client/server code, but it provided strongly typed messages and standard status codes. REST handled the slow dependency with an HTTP timeout, while gRPC used a deadline and reported `DEADLINE_EXCEEDED`. The two implementations used different error representations, but both returned a clear failure to the caller and kept the Order Service running. gRPC involved more setup, while REST was easier to inspect manually with `curl`.

## Regenerating the gRPC files

If `inventory.proto` changes, regenerate the Python modules with:

```bash
python -m grpc_tools.protoc \
  -I grpc_version \
  --python_out=grpc_version \
  --grpc_python_out=grpc_version \
  grpc_version/inventory.proto
```
