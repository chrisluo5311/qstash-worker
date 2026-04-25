# qstash-worker

A lightweight Python task queue framework built on [Upstash QStash](https://upstash.com/qstash). Deploy workers anywhere with just `pip install` + a `.env` file.

## Why?

- **No infrastructure to manage** — QStash handles retries, DLQ, scheduling, and delivery guarantees
- **Zero-config deployment** — Drop a `.env` file on any server and start receiving tasks
- **HTTP-based** — Works across languages, cloud providers, and network boundaries
- **Type-safe** — Pydantic models for payloads and results

## Quick Start

### 1. Install

```bash
pip install qstash-worker
```

### 2. Configure

Create a `.env` file:

```bash
QSTASH_TOKEN=your_qstash_token
QSTASH_CURRENT_SIGNING_KEY=your_current_signing_key
QSTASH_NEXT_SIGNING_KEY=your_next_signing_key
QSTASH_CALLBACK_URL=http://your-server:8081/results  # optional
```

### 3. Write a Worker (Consumer)

```python
# worker.py
import subprocess
from qstash_worker import task, default_worker

@task("coding")
def handle_coding(payload):
    result = subprocess.run(
        payload["command"],
        shell=True,
        capture_output=True,
        text=True,
        timeout=300,
    )
    return {
        "stdout": result.stdout,
        "stderr": result.stderr,
        "returncode": result.returncode,
    }

@task("git_pull")
def handle_git_pull(payload):
    repo = payload.get("repo", "/app")
    result = subprocess.run(
        ["git", "-C", repo, "pull"],
        capture_output=True,
        text=True,
    )
    return {"output": result.stdout}

if __name__ == "__main__":
    default_worker.run(host="0.0.0.0", port=8080)
```

Run it:

```bash
python worker.py
```

### 4. Send Tasks (Producer)

```python
# producer.py
from qstash_worker import TaskClient

client = TaskClient()

msg_id = client.send(
    task_type="coding",
    payload={"command": "echo 'Hello, World!'"},
    url="http://your-worker:8080/tasks",
    queue="coding-tasks",           # ordered execution
    callback="http://your-server:8081/results",
    timeout="300s",
    retries=3,
    flow_control={
        "key": "gpu-worker",
        "rate_per_second": 1,
        "parallelism": 1,
    },
)
print(f"Task sent: {msg_id}")
```

### 5. Receive Callbacks

```python
# callback_server.py
from fastapi import FastAPI
from qstash_worker import TaskResult

app = FastAPI()

@app.post("/results")
async def receive_result(result: TaskResult):
    print(f"Task {result.task_type}: {result.status}")
    return {"ok": True}
```

## Docker

```bash
docker build -f docker/Dockerfile -t qstash-worker .
docker run -p 8080:8080 --env-file .env qstash-worker
```

Or use docker-compose:

```bash
cd docker
docker-compose up
```

## Features

| Feature | How |
|---------|-----|
| Task routing | `@task("coding")` decorator |
| Ordered execution | `queue="coding-tasks"` |
| Rate limiting | `flow_control={"rate_per_second": 2}` |
| Auto-retry | `retries=3` (default) |
| Timeout | `timeout="300s"` |
| Result callback | `callback="http://..."` |
| Signature verification | Automatic with QStash signing keys |
| Async handlers | `@task("deploy") async def handle_deploy(...)` |

## API Reference

### `TaskClient`

```python
client = TaskClient()

client.send(
    task_type="str",           # Task identifier
    payload=dict,              # Task arguments
    url="str",                 # Consumer endpoint
    queue="str",               # Queue name (optional)
    callback="str",            # Result callback URL (optional)
    delay="str",               # Delay (e.g., "5m", "1h")
    timeout="str",             # Max execution time (e.g., "300s")
    retries=int,               # Retry count
    flow_control=dict,         # {"key": "...", "rate_per_second": 2, "parallelism": 1}
)

client.batch_send([{...}, {...}])  # Send multiple tasks
```

### `TaskWorker`

```python
from qstash_worker import TaskWorker

worker = TaskWorker()

@worker.register("task_type")
def handler(payload):
    return {"result": "ok"}

worker.run(host="0.0.0.0", port=8080)
```

## Development

```bash
# Clone
git clone https://github.com/chrisluo5311/qstash-worker.git
cd qstash-worker

# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Lint
ruff check qstash_worker tests examples
ruff format qstash_worker tests examples

# Type check
mypy qstash_worker
```

## License

MIT
