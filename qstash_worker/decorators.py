"""Convenience decorators for task registration."""

from typing import Callable, Optional

from .worker import TaskWorker

# Global default worker instance (lazy)
_default_worker: Optional[TaskWorker] = None


def get_default_worker() -> TaskWorker:
    """Get or create global worker instance."""
    global _default_worker
    if _default_worker is None:
        _default_worker = TaskWorker()
    return _default_worker


def task(task_type: str) -> Callable:
    """Decorator to register a task handler on the default worker.

    Usage:
        from qstash_worker import task

        @task("coding")
        def handle_coding(payload):
            ...
    """
    return get_default_worker().register(task_type)
