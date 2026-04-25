#!/usr/bin/env python3
"""Example producer: send tasks to QStash."""

import os

from qstash_worker import TaskClient


def main() -> None:
    client = TaskClient()

    # Replace with your consumer endpoint URL
    consumer_url = os.getenv("CONSUMER_URL", "http://208.84.103.172:8080/tasks")

    # Send a coding task
    msg_id = client.send(
        task_type="coding",
        payload={
            "command": "echo 'Hello from QStash Worker!'",
            "timeout": 60,
        },
        url=consumer_url,
        queue="coding-tasks",
        timeout="300s",
        retries=3,
    )
    print(f"Sent coding task: {msg_id}")

    # Send a git_pull task
    msg_id2 = client.send(
        task_type="git_pull",
        payload={"repo": "/home/admin/project"},
        url=consumer_url,
        queue="coding-tasks",
    )
    print(f"Sent git_pull task: {msg_id2}")

    # Batch send example
    batch_tasks = [
        {
            "task_type": "coding",
            "payload": {"command": f"echo 'task {i}'"},
            "url": consumer_url,
            "queue": "coding-tasks",
        }
        for i in range(3)
    ]
    ids = client.batch_send(batch_tasks)
    print(f"Batch sent: {ids}")


if __name__ == "__main__":
    main()
