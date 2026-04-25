#!/usr/bin/env python3
"""Example callback server: receive task results."""

from fastapi import FastAPI
from pydantic import BaseModel
from typing import Any, Optional

app = FastAPI(title="Task Callback Server")


class CallbackPayload(BaseModel):
    task_id: Optional[str] = None
    task_type: str
    status: str
    result: Any = None
    error: Optional[str] = None
    duration_ms: Optional[int] = None


@app.post("/results")
async def receive_result(payload: CallbackPayload) -> dict:
    print(f"[RESULT] {payload.task_type} -> {payload.status} ({payload.duration_ms}ms)")
    if payload.error:
        print(f"  Error: {payload.error[:200]}")
    return {"ok": True}


@app.post("/failures")
async def receive_failure(payload: CallbackPayload) -> dict:
    print(f"[FAILURE] {payload.task_type} -> {payload.error}")
    return {"ok": True}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8081)
