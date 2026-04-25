"""Consumer worker with FastAPI for receiving QStash tasks."""

import inspect
import time
import traceback
from typing import Any, Callable, Dict, Optional

from fastapi import FastAPI, HTTPException, Request
from qstash import Receiver

from .config import config
from .models import TaskPayload, TaskResult, TaskStatus


class TaskWorker:
    """FastAPI-based worker that receives and routes QStash tasks."""

    def __init__(
        self,
        title: str = "QStash Worker",
        verify_signature: bool = True,
    ) -> None:
        """Initialize worker.

        Args:
            title: FastAPI app title.
            verify_signature: Whether to verify QStash signatures. Disable for local testing.
        """
        self.app = FastAPI(title=title)
        self.handlers: Dict[str, Callable[..., Any]] = {}
        self._verify_signature = verify_signature
        self._receiver: Optional[Receiver] = None

        if verify_signature:
            self._receiver = Receiver(
                current_signing_key=config.current_signing_key,
                next_signing_key=config.next_signing_key,
            )

        self._setup_routes()

    def _setup_routes(self) -> None:
        """Register FastAPI routes."""

        @self.app.post("/tasks")
        async def handle_task(request: Request) -> dict[str, Any]:
            body_bytes = await request.body()

            # Verify QStash signature
            if self._verify_signature and self._receiver is not None:
                signature = request.headers.get("Upstash-Signature", "")
                try:
                    self._receiver.verify(
                        body=body_bytes,
                        signature=signature,
                        url=str(request.url),
                    )
                except Exception as exc:
                    raise HTTPException(
                        status_code=401,
                        detail=f"Invalid signature: {exc}",
                    ) from exc

            # Parse payload
            data = await request.json()
            task = TaskPayload(**data)

            # Route to handler
            handler = self.handlers.get(task.task_type)
            if handler is None:
                raise HTTPException(
                    status_code=404,
                    detail=f"No handler registered for task type: {task.task_type}",
                )

            # Execute task
            start = time.time()
            try:
                if inspect.iscoroutinefunction(handler):
                    result = await handler(task.payload)
                else:
                    result = handler(task.payload)

                duration = int((time.time() - start) * 1000)
                return TaskResult(
                    task_id=task.task_id,
                    task_type=task.task_type,
                    status=TaskStatus.SUCCESS,
                    result=result,
                    duration_ms=duration,
                ).model_dump()

            except Exception as exc:
                duration = int((time.time() - start) * 1000)
                error_msg = f"{exc}\n{traceback.format_exc()}"
                # Return 500 so QStash retries if retries remain
                raise HTTPException(
                    status_code=500,
                    detail=TaskResult(
                        task_id=task.task_id,
                        task_type=task.task_type,
                        status=TaskStatus.FAILED,
                        error=error_msg,
                        duration_ms=duration,
                    ).model_dump(),
                ) from exc

        @self.app.get("/health")
        def health() -> dict[str, Any]:
            return {
                "status": "ok",
                "handlers": list(self.handlers.keys()),
                "version": "0.1.0",
            }

    def register(self, task_type: str) -> Callable:
        """Decorator to register a task handler.

        Usage:
            @worker.register("coding")
            def handle_coding(payload):
                ...
        """

        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            self.handlers[task_type] = func
            return func

        return decorator

    def run(self, host: str = "0.0.0.0", port: int = 8080) -> None:
        """Run the worker with uvicorn.

        Args:
            host: Bind host.
            port: Bind port.
        """
        import uvicorn

        print(f"Registered handlers: {list(self.handlers.keys())}")
        uvicorn.run(self.app, host=host, port=port)
