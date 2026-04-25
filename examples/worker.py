#!/usr/bin/env python3
"""Example consumer: receive and execute tasks from QStash."""

import subprocess

from qstash_worker import default_worker, task


@task("coding")
def handle_coding(payload: dict) -> dict:
    """Execute a shell command."""
    command = payload.get("command", "")
    timeout = payload.get("timeout", 300)

    result = subprocess.run(
        command,
        shell=True,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return {
        "stdout": result.stdout,
        "stderr": result.stderr,
        "returncode": result.returncode,
    }


@task("git_pull")
def handle_git_pull(payload: dict) -> dict:
    """Run git pull in a repository."""
    repo = payload.get("repo", "/app")
    result = subprocess.run(
        ["git", "-C", repo, "pull"],
        capture_output=True,
        text=True,
        timeout=60,
    )
    return {
        "stdout": result.stdout,
        "stderr": result.stderr,
        "returncode": result.returncode,
    }


@task("deploy")
async def handle_deploy(payload: dict) -> dict:
    """Async task example: deploy a service."""
    service = payload.get("service", "app")
    # Simulate async work
    import asyncio

    await asyncio.sleep(1)
    return {"status": "deployed", "service": service}


if __name__ == "__main__":
    print(f"Starting worker with handlers: {list(default_worker.handlers.keys())}")
    default_worker.run(host="0.0.0.0", port=8080)
