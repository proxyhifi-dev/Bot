import logging
from typing import Any, Dict, Optional

import requests

from health import CircuitBreaker
from utils import FyersConfig, compute_backoff, sleep_with_log


class FyersAdapter:
    def __init__(self, config: FyersConfig, access_token: str, logger: logging.Logger):
        self.config = config
        self.access_token = access_token
        self.logger = logger
        self.circuit_breaker = CircuitBreaker(failure_threshold=5, cooldown_seconds=90)

    @property
    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"{self.config.client_id}:{self.access_token}",
            "Content-Type": "application/json",
        }

    def _request(self, method: str, path: str, **kwargs: Any) -> Dict[str, Any]:
        if self.circuit_breaker.is_open:
            raise RuntimeError("Circuit breaker is OPEN. Trading calls are paused due to API instability.")

        url = f"{self.config.base_url}{path}"
        headers = kwargs.pop("headers", {})
        merged_headers = {**self._headers, **headers}

        for attempt in range(1, self.config.max_retries + 1):
            try:
                response = requests.request(
                    method,
                    url,
                    headers=merged_headers,
                    timeout=self.config.timeout_seconds,
                    **kwargs,
                )

                if response.status_code == 429:
                    delay = compute_backoff(self.config.backoff_base, attempt)
                    sleep_with_log(self.logger, "Rate limit (429)", delay)
                    continue

                if response.status_code in (502, 503):
                    self.circuit_breaker.register_failure()
                    delay = compute_backoff(max(self.config.backoff_base, 2.0), attempt, cap=120)
                    sleep_with_log(self.logger, f"Gateway issue ({response.status_code})", delay)
                    continue

                response.raise_for_status()
                self.circuit_breaker.register_success()
                return response.json()

            except requests.RequestException as exc:
                self.circuit_breaker.register_failure()
                if attempt == self.config.max_retries:
                    self.logger.error(
                        "API request failed",
                        extra={"details": {"path": path, "error": str(exc)}},
                    )
                    raise RuntimeError(f"API request failed: {exc}") from exc
                delay = compute_backoff(self.config.backoff_base, attempt)
                sleep_with_log(self.logger, "Request exception", delay)

        raise RuntimeError(f"Request failed after retries: {path}")

    def get_ltp(self, symbol: str) -> Dict[str, Any]:
        return self._request("GET", "/data/quotes", params={"symbols": symbol})

    def get_history(
        self,
        symbol: str,
        resolution: str,
        range_from: str,
        range_to: str,
        date_format: str = "1",
        cont_flag: str = "1",
    ) -> Dict[str, Any]:
        params = {
            "symbol": symbol,
            "resolution": resolution,
            "date_format": date_format,
            "range_from": range_from,
            "range_to": range_to,
            "cont_flag": cont_flag,
        }
        return self._request("GET", "/data/history", params=params)

    def place_order(self, order_payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._request("POST", "/api/v3/orders", json=order_payload)

    def modify_order(self, order_payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._request("PATCH", "/api/v3/orders", json=order_payload)

    def cancel_order(self, order_id: str) -> Dict[str, Any]:
        return self._request("DELETE", "/api/v3/orders", json={"id": order_id})

    def get_orderbook(self) -> Dict[str, Any]:
        return self._request("GET", "/api/v3/orderbook")

    def get_positions(self) -> Dict[str, Any]:
        return self._request("GET", "/api/v3/positions")

    def get_funds(self) -> Dict[str, Any]:
        return self._request("GET", "/api/v3/funds")

    def update_access_token(self, token: str) -> None:
        self.access_token = token

    def get_profile(self) -> Dict[str, Any]:
        return self._request("GET", "/api/v3/profile")

    def raw_request(self, method: str, path: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        kwargs: Dict[str, Any] = {}
        if payload:
            kwargs["json"] = payload
        return self._request(method=method, path=path, **kwargs)
