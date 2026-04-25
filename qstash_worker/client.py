"""Producer client for sending tasks via QStash."""

from typing import Any, Optional

from qstash import QStash

from .config import QStashConfig, config
from .models import TaskPayload


class TaskClient:
    """Client for publishing tasks to QStash queue."""

    def __init__(self, token: Optional[str] = None) -> None:
        """Initialize QStash client.

        Args:
            token: QStash token. If not provided, uses QSTASH_TOKEN from environment.
        """
        cfg = config if token is None else QStashConfig(token=token)
        self.client = QStash(cfg.token)
        self._config = cfg

    def send(
        self,
        task_type: str,
        payload: dict[str, Any],
        url: str,
        queue: Optional[str] = None,
        callback: Optional[str] = None,
        delay: Optional[str] = None,
        timeout: Optional[str] = None,
        retries: Optional[int] = None,
        flow_control: Optional[dict[str, Any]] = None,
    ) -> str:
        """Send a task to QStash.

        Args:
            task_type: Task type (e.g., 'coding', 'git_pull').
            payload: Task arguments.
            url: Consumer endpoint URL.
            queue: Queue name for ordered execution.
            callback: URL to receive result callback.
            delay: Delay before execution (e.g., '5m', '1h').
            timeout: Max execution time (e.g., '300s').
            retries: Number of retries on failure.
            flow_control: Rate limiting config with 'key', 'rate_per_second', 'parallelism'.

        Returns:
            QStash message ID.
        """
        body = TaskPayload(
            task_type=task_type,
            payload=payload,
        ).model_dump()

        kwargs: dict[str, Any] = {
            "url": url,
            "body": body,
            "retries": retries or self._config.default_retries,
            "timeout": timeout or self._config.default_timeout,
        }

        if queue:
            kwargs["queue"] = queue
        if callback or self._config.callback_url:
            kwargs["callback"] = callback or self._config.callback_url
        if delay:
            kwargs["delay"] = delay
        if flow_control:
            kwargs["flow_control"] = flow_control

        res = self.client.message.publish_json(**kwargs)
        if isinstance(res, list):
            return res[0].message_id
        return res.message_id

    def batch_send(self, tasks: list[dict[str, Any]]) -> list[str]:
        """Send multiple tasks in batch.

        Args:
            tasks: List of task kwargs dicts.

        Returns:
            List of QStash message IDs.
        """
        message_ids: list[str] = []
        for task_kwargs in tasks:
            mid = self.send(**task_kwargs)
            message_ids.append(mid)
        return message_ids


# Global singleton client
default_client = TaskClient()
