from __future__ import annotations

import json
import logging
import os
import threading
import time
from typing import Dict, List

import requests


class FyersAdapter:
    """Official-Fyers style adapter with OAuth/token validation, retries and rate-limit handling."""

    def __init__(self):
        self.logger = logging.getLogger("fyers_adapter")
        self.client_id = os.getenv("FYERS_CLIENT_ID", "")
        self.secret_key = os.getenv("FYERS_SECRET_KEY", "")
        self.redirect_uri = os.getenv("FYERS_REDIRECT_URI", "")
        self.access_token = os.getenv("FYERS_ACCESS_TOKEN", "")
        self.base_url = os.getenv("FYERS_BASE_URL", "https://api-t1.fyers.in")

        self.session = requests.Session()

        self._order_dedupe = set()
        self._order_dedupe_lock = threading.Lock()
        self._max_retries = 5
        self._base_backoff = 0.5

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"{self.client_id}:{self.access_token}",
            "Content-Type": "application/json",
        }

    def _request_with_backoff(self, method: str, path: str, **kwargs) -> requests.Response:
        url = f"{self.base_url}{path}"
        last_exc = None
        for attempt in range(self._max_retries + 1):
            try:
                resp = self.session.request(method=method, url=url, timeout=10, **kwargs)
                if resp.status_code == 429:
                    if attempt >= self._max_retries:
                        self.logger.error(
                            "rate_limit_exhausted method=%s path=%s attempts=%s",
                            method,
                            path,
                            attempt + 1,
                        )
                        resp.raise_for_status()
                    backoff = self._base_backoff * (2**attempt)
                    self.logger.warning(
                        "rate_limit method=%s path=%s status=%s attempt=%s backoff_s=%.2f",
                        method,
                        path,
                        resp.status_code,
                        attempt + 1,
                        backoff,
                    )
                    time.sleep(backoff)
                    continue
                resp.raise_for_status()
                return resp
            except requests.RequestException as exc:
                last_exc = exc
                if getattr(getattr(exc, "response", None), "status_code", None) == 429:
                    continue
                if attempt >= self._max_retries:
                    break
                backoff = self._base_backoff * (2**attempt)
                self.logger.warning(
                    "network_retry method=%s path=%s attempt=%s backoff_s=%.2f error=%s",
                    method,
                    path,
                    attempt + 1,
                    backoff,
                    exc,
                )
                time.sleep(backoff)

        if last_exc:
            raise last_exc
        raise RuntimeError(f"Unhandled request failure for {method} {path}")

    def get_login_url(self, state: str = "bot") -> str:
        return (
            "https://api-t1.fyers.in/api/v3/generate-authcode"
            f"?client_id={self.client_id}&redirect_uri={self.redirect_uri}&response_type=code&state={state}"
        )

    def exchange_auth_code(self, auth_code: str) -> Dict:
        payload = {
            "grant_type": "authorization_code",
            "appIdHash": self.client_id,
            "code": auth_code,
        }
        resp = self._request_with_backoff("POST", "/api/v3/token", json=payload)
        data = resp.json()
        token = data.get("access_token")
        if token:
            self.access_token = token
        return data

    def validate_token(self) -> bool:
        if not self.access_token or not self.client_id:
            return False
        try:
            resp = self._request_with_backoff("GET", "/api/v3/profile", headers=self._headers())
            if resp.status_code == 200:
                return True
            self.logger.warning("Token validation failed status=%s body=%s", resp.status_code, resp.text)
            return False
        except requests.RequestException as exc:
            self.logger.error("Token validation error: %s", exc)
            return False

    def get_ltp(self, symbol: str) -> float:
        payload = {"symbols": symbol}
        resp = self._request_with_backoff("GET", "/data/quotes", params=payload, headers=self._headers())
        data = resp.json()
        ltp = data.get("d", [{}])[0].get("v", {}).get("lp")
        if ltp is None:
            raise ValueError(f"LTP not available for {symbol}: {json.dumps(data)}")
        return float(ltp)

    def get_history(
        self,
        symbol: str,
        resolution: str = "5",
        range_from: str = "1704067200",
        range_to: str = "1706745600",
    ) -> List[List[float]]:
        payload = {
            "symbol": symbol,
            "resolution": resolution,
            "date_format": "0",
            "range_from": range_from,
            "range_to": range_to,
            "cont_flag": "1",
        }
        resp = self._request_with_backoff("GET", "/data/history", params=payload, headers=self._headers())
        data = resp.json()
        return data.get("candles", [])

    def place_order(self, order: Dict) -> Dict:
        dedupe_key = f"{order.get('symbol')}|{order.get('side')}|{order.get('qty')}|{order.get('type')}"
        with self._order_dedupe_lock:
            if dedupe_key in self._order_dedupe:
                raise ValueError("Duplicate order blocked")
            self._order_dedupe.add(dedupe_key)

        try:
            resp = self._request_with_backoff("POST", "/api/v3/orders", json=order, headers=self._headers())
            return resp.json()
        except Exception:
            with self._order_dedupe_lock:
                self._order_dedupe.discard(dedupe_key)
            raise

    def get_positions(self) -> List[Dict]:
        resp = self._request_with_backoff("GET", "/api/v3/positions", headers=self._headers())
        return resp.json().get("netPositions", [])
