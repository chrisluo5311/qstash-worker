"""Convenience decorators for task registration."""

from typing import Callable

from .worker import TaskWorker

# Global default worker instance
default_worker = TaskWorker()


def task(task_type: str) -> Callable:
    """Decorator to register a task handler on the default worker.

    Usage:
        from qstash_worker import task

        @task("coding")
        def handle_coding(payload):
            ...
    """
    return default_worker.register(task_type)
