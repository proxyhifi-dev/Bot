from __future__ import annotations

import json
import logging
import os
from typing import Dict, List, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


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
        retries = Retry(
            total=5,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"],
        )
        self.session.mount("https://", HTTPAdapter(max_retries=retries))

        self._order_dedupe = set()

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"{self.client_id}:{self.access_token}",
            "Content-Type": "application/json",
        }

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
        resp = self.session.post(f"{self.base_url}/api/v3/token", json=payload, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        token = data.get("access_token")
        if token:
            self.access_token = token
        return data

    def validate_token(self) -> bool:
        if not self.access_token or not self.client_id:
            return False
        try:
            resp = self.session.get(
                f"{self.base_url}/api/v3/profile", headers=self._headers(), timeout=10
            )
            if resp.status_code == 200:
                return True
            self.logger.warning("Token validation failed status=%s body=%s", resp.status_code, resp.text)
            return False
        except requests.RequestException as exc:
            self.logger.error("Token validation error: %s", exc)
            return False

    def get_ltp(self, symbol: str) -> float:
        payload = {"symbols": symbol}
        resp = self.session.get(
            f"{self.base_url}/data/quotes", params=payload, headers=self._headers(), timeout=10
        )
        resp.raise_for_status()
        data = resp.json()
        ltp = data.get("d", [{}])[0].get("v", {}).get("lp")
        if ltp is None:
            raise ValueError(f"LTP not available for {symbol}: {json.dumps(data)}")
        return float(ltp)

    def get_history(self, symbol: str, resolution: str = "5", range_from: str = "1704067200", range_to: str = "1706745600") -> List[List[float]]:
        payload = {
            "symbol": symbol,
            "resolution": resolution,
            "date_format": "0",
            "range_from": range_from,
            "range_to": range_to,
            "cont_flag": "1",
        }
        resp = self.session.get(
            f"{self.base_url}/data/history", params=payload, headers=self._headers(), timeout=10
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("candles", [])

    def place_order(self, order: Dict) -> Dict:
        dedupe_key = f"{order.get('symbol')}|{order.get('side')}|{order.get('qty')}|{order.get('type')}"
        if dedupe_key in self._order_dedupe:
            raise ValueError("Duplicate order blocked")
        self._order_dedupe.add(dedupe_key)

        resp = self.session.post(
            f"{self.base_url}/api/v3/orders", json=order, headers=self._headers(), timeout=10
        )
        if resp.status_code == 429:
            raise RuntimeError("Fyers rate limit reached")
        resp.raise_for_status()
        return resp.json()

    def get_positions(self) -> List[Dict]:
        resp = self.session.get(
            f"{self.base_url}/api/v3/positions", headers=self._headers(), timeout=10
        )
        resp.raise_for_status()
        return resp.json().get("netPositions", [])
