import logging
import time
from dataclasses import dataclass
from typing import Optional

import requests

from utils import FyersConfig


@dataclass
class HealthStatus:
    healthy: bool
    status_code: Optional[int]
    message: str


class CircuitBreaker:
    def __init__(self, failure_threshold: int = 5, cooldown_seconds: int = 90):
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds
        self.failure_count = 0
        self.opened_at: Optional[float] = None

    @property
    def is_open(self) -> bool:
        if self.opened_at is None:
            return False
        elapsed = time.time() - self.opened_at
        if elapsed >= self.cooldown_seconds:
            self.opened_at = None
            self.failure_count = 0
            return False
        return True

    def register_failure(self) -> None:
        self.failure_count += 1
        if self.failure_count >= self.failure_threshold:
            self.opened_at = time.time()

    def register_success(self) -> None:
        self.failure_count = 0
        self.opened_at = None


def check_api_health(config: FyersConfig, logger: logging.Logger) -> HealthStatus:
    url = config.base_url
    try:
        response = requests.get(url, timeout=config.timeout_seconds)
        if response.status_code == 503:
            logger.error(
                "Fyers API unhealthy - service unavailable",
                extra={"details": {"status_code": 503, "url": url}},
            )
            return HealthStatus(False, response.status_code, "Service unavailable (503).")
        if response.status_code >= 500:
            return HealthStatus(False, response.status_code, "Gateway/server error.")
        return HealthStatus(True, response.status_code, "API healthy.")
    except requests.RequestException as exc:
        logger.error(
            "Health check failed",
            extra={"details": {"error": str(exc), "url": url}},
        )
        return HealthStatus(False, None, str(exc))
