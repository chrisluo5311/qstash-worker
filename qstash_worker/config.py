"""Auto-load configuration from environment variables."""

import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()


@dataclass
class QStashConfig:
    """QStash configuration loaded from environment variables."""

    token: str = ""
    current_signing_key: str = ""
    next_signing_key: str = ""
    callback_url: str = ""
    default_timeout: str = "300s"
    default_retries: int = 3

    def __post_init__(self) -> None:
        """Load values from environment if not explicitly set."""
        self.token = self.token or os.getenv("QSTASH_TOKEN", "")
        self.current_signing_key = self.current_signing_key or os.getenv(
            "QSTASH_CURRENT_SIGNING_KEY", ""
        )
        self.next_signing_key = self.next_signing_key or os.getenv(
            "QSTASH_NEXT_SIGNING_KEY", ""
        )
        self.callback_url = self.callback_url or os.getenv("QSTASH_CALLBACK_URL", "")

        if not self.token:
            raise ValueError(
                "QSTASH_TOKEN is required. Set it via environment variable or pass to QStashConfig."
            )


# Global singleton config
config = QStashConfig()
