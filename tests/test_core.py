"""Tests for qstash-worker core functionality."""

import os
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from qstash_worker import TaskClient, TaskPayload, TaskResult, TaskStatus, TaskWorker, task
from qstash_worker.config import QStashConfig


class TestConfig:
    """Test configuration loading."""

    def test_config_from_env(self, monkeypatch):
        monkeypatch.setenv("QSTASH_TOKEN", "test-token")
        monkeypatch.setenv("QSTASH_CURRENT_SIGNING_KEY", "current-key")
        monkeypatch.setenv("QSTASH_NEXT_SIGNING_KEY", "next-key")

        cfg = QStashConfig()
        assert cfg.token == "test-token"
        assert cfg.current_signing_key == "current-key"
        assert cfg.next_signing_key == "next-key"

    def test_config_missing_token_raises(self):
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="QSTASH_TOKEN is required"):
                QStashConfig()

    def test_config_explicit_values(self):
        cfg = QStashConfig(
            token="explicit-token",
            current_signing_key="ck",
            next_signing_key="nk",
        )
        assert cfg.token == "explicit-token"


class TestModels:
    """Test Pydantic models."""

    def test_task_payload_creation(self):
        payload = TaskPayload(task_type="coding", payload={"command": "echo hi"})
        assert payload.task_type == "coding"
        assert payload.payload == {"command": "echo hi"}
        assert payload.task_id is None

    def test_task_result_creation(self):
        result = TaskResult(
            task_type="coding",
            status=TaskStatus.SUCCESS,
            result={"stdout": "hi"},
            duration_ms=100,
        )
        assert result.status == TaskStatus.SUCCESS
        assert result.error is None


class TestTaskClient:
    """Test TaskClient producer."""

    @patch("qstash_worker.client.QStash")
    def test_send_task(self, mock_qstash_class):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.message_id = "msg-123"
        mock_client.message.publish_json.return_value = mock_response
        mock_qstash_class.return_value = mock_client

        client = TaskClient(token="test-token")
        msg_id = client.send(
            task_type="coding",
            payload={"command": "echo hello"},
            url="http://localhost:8080/tasks",
        )

        assert msg_id == "msg-123"
        mock_client.message.publish_json.assert_called_once()
        call_kwargs = mock_client.message.publish_json.call_args.kwargs
        assert call_kwargs["url"] == "http://localhost:8080/tasks"
        assert call_kwargs["body"]["task_type"] == "coding"
        assert call_kwargs["retries"] == 3
        assert call_kwargs["timeout"] == "300s"

    @patch("qstash_worker.client.QStash")
    def test_send_with_queue(self, mock_qstash_class):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.message_id = "msg-456"
        mock_client.message.publish_json.return_value = mock_response
        mock_qstash_class.return_value = mock_client

        client = TaskClient(token="test-token")
        msg_id = client.send(
            task_type="git_pull",
            payload={"repo": "/app"},
            url="http://localhost:8080/tasks",
            queue="default",
            delay="5m",
            timeout="600s",
            retries=5,
            flow_control={"key": "app", "rate_per_second": 2, "parallelism": 1},
        )

        assert msg_id == "msg-456"
        call_kwargs = mock_client.message.publish_json.call_args.kwargs
        assert call_kwargs["queue"] == "default"
        assert call_kwargs["delay"] == "5m"
        assert call_kwargs["timeout"] == "600s"
        assert call_kwargs["retries"] == 5
        assert call_kwargs["flow_control"]["key"] == "app"

    @patch("qstash_worker.client.QStash")
    def test_batch_send(self, mock_qstash_class):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.message_id = "batch-msg"
        mock_client.message.publish_json.return_value = mock_response
        mock_qstash_class.return_value = mock_client

        client = TaskClient(token="test-token")
        tasks = [
            {
                "task_type": "coding",
                "payload": {"cmd": "echo 1"},
                "url": "http://localhost/tasks",
            },
            {
                "task_type": "coding",
                "payload": {"cmd": "echo 2"},
                "url": "http://localhost/tasks",
            },
        ]
        ids = client.batch_send(tasks)
        assert len(ids) == 2
        assert mock_client.message.publish_json.call_count == 2


class TestTaskWorker:
    """Test TaskWorker consumer."""

    def test_worker_initialization(self):
        worker = TaskWorker(verify_signature=False)
        assert len(worker.handlers) == 0
        assert worker._verify_signature is False

    def test_register_handler(self):
        worker = TaskWorker(verify_signature=False)

        @worker.register("test_task")
        def handle_test(payload):
            return {"ok": True}

        assert "test_task" in worker.handlers
        assert worker.handlers["test_task"]({}) == {"ok": True}

    def test_health_endpoint(self):
        worker = TaskWorker(verify_signature=False)
        client = TestClient(worker.app)
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["handlers"] == []

    def test_task_endpoint_sync_handler(self):
        worker = TaskWorker(verify_signature=False)

        @worker.register("add")
        def handle_add(payload):
            return {"sum": payload["a"] + payload["b"]}

        client = TestClient(worker.app)
        response = client.post(
            "/tasks",
            json={
                "task_type": "add",
                "payload": {"a": 2, "b": 3},
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["result"]["sum"] == 5
        assert data["task_type"] == "add"
        assert data["duration_ms"] is not None

    @pytest.mark.asyncio
    async def test_task_endpoint_async_handler(self):
        worker = TaskWorker(verify_signature=False)

        @worker.register("async_task")
        async def handle_async(payload):
            import asyncio

            await asyncio.sleep(0.01)
            return {"done": True}

        client = TestClient(worker.app)
        response = client.post(
            "/tasks",
            json={
                "task_type": "async_task",
                "payload": {},
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["result"]["done"] is True

    def test_task_endpoint_unknown_type(self):
        worker = TaskWorker(verify_signature=False)
        client = TestClient(worker.app)
        response = client.post(
            "/tasks",
            json={
                "task_type": "unknown",
                "payload": {},
            },
        )

        assert response.status_code == 404

    def test_task_endpoint_handler_error(self):
        worker = TaskWorker(verify_signature=False)

        @worker.register("fail")
        def handle_fail(payload):
            raise ValueError("intentional error")

        client = TestClient(worker.app)
        response = client.post(
            "/tasks",
            json={
                "task_type": "fail",
                "payload": {},
            },
        )

        assert response.status_code == 500
        data = response.json()
        assert "detail" in data
        detail = data["detail"]
        assert detail["status"] == "failed"
        assert "intentional error" in detail["error"]


class TestDecorators:
    """Test convenience decorators."""

    def test_task_decorator(self):
        from qstash_worker.decorators import default_worker

        @task("decorated_task")
        def handle_decorated(payload):
            return {"received": payload}

        assert "decorated_task" in default_worker.handlers
        result = default_worker.handlers["decorated_task"]({"key": "value"})
        assert result == {"received": {"key": "value"}}
