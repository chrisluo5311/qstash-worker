"""Pydantic models for task payloads and results."""

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    """Task execution status."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


class TaskPayload(BaseModel):
    """Payload sent from producer to consumer via QStash."""

    task_type: str = Field(..., description="Task type identifier (e.g., 'coding')")
    payload: dict[str, Any] = Field(default_factory=dict, description="Task arguments")
    task_id: Optional[str] = Field(default=None, description="Optional task ID for tracking")
    callback_url: Optional[str] = Field(default=None, description="Override callback URL")


class TaskResult(BaseModel):
    """Result returned by consumer after task execution."""

    task_id: Optional[str] = Field(default=None)
    task_type: str
    status: TaskStatus
    result: Any = None
    error: Optional[str] = None
    duration_ms: Optional[int] = None
