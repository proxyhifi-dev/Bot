import logging
import time
from dataclasses import dataclass
from typing import Optional

import requests

from utils import FyersConfig, compute_backoff, sleep_with_log


@dataclass
class HealthStatus:
    healthy: bool
    status_code: Optional[int]
    message: str
    selected_base_url: Optional[str] = None


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


def _is_healthy_status(status_code: int) -> bool:
    # For probe endpoint, 200/302/400/401/403/405 indicate server is reachable.
    return status_code in {200, 302, 400, 401, 403, 405}


def _probe_base_url(base_url: str, config: FyersConfig, logger: logging.Logger) -> HealthStatus:
    probe_url = f"{base_url}{config.health_probe_path}"

    for attempt in range(1, config.max_retries + 1):
        try:
            response = requests.get(probe_url, timeout=config.timeout_seconds, allow_redirects=False)
            if _is_healthy_status(response.status_code):
                return HealthStatus(
                    healthy=True,
                    status_code=response.status_code,
                    message="API healthy.",
                    selected_base_url=base_url,
                )

            if response.status_code in (429, 502, 503):
                if attempt == config.max_retries:
                    break
                delay = compute_backoff(config.backoff_base, attempt)
                sleep_with_log(
                    logger,
                    f"Health probe retry for status {response.status_code} on {base_url}",
                    delay,
                )
                continue

            return HealthStatus(
                healthy=False,
                status_code=response.status_code,
                message=f"Probe returned unexpected status {response.status_code}.",
                selected_base_url=base_url,
            )

        except requests.RequestException as exc:
            if attempt == config.max_retries:
                return HealthStatus(False, None, str(exc), selected_base_url=base_url)
            delay = compute_backoff(config.backoff_base, attempt)
            sleep_with_log(logger, f"Health probe request error on {base_url}", delay)

    return HealthStatus(
        healthy=False,
        status_code=503,
        message="Service unavailable after retries.",
        selected_base_url=base_url,
    )


def check_api_health(config: FyersConfig, logger: logging.Logger) -> HealthStatus:
    candidates = [config.base_url, *config.fallback_base_urls]
    seen = set()

    for base_url in candidates:
        if base_url in seen:
            continue
        seen.add(base_url)

        status = _probe_base_url(base_url, config, logger)
        if status.healthy:
            if config.base_url != base_url:
                logger.warning(
                    "Switched to fallback FYERS base URL",
                    extra={"details": {"previous": config.base_url, "selected": base_url}},
                )
            config.base_url = base_url
            return status

        logger.error(
            "Fyers API health probe failed",
            extra={
                "details": {
                    "base_url": base_url,
                    "status_code": status.status_code,
                    "message": status.message,
                    "probe_path": config.health_probe_path,
                }
            },
        )

    return HealthStatus(False, 503, "All configured FYERS base URLs are unhealthy.", selected_base_url=None)
