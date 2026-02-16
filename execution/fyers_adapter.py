from __future__ import annotations

import hashlib
import json
import logging
import os
from pathlib import Path
from typing import Dict, List

try:
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
except ModuleNotFoundError:
    requests = None
    HTTPAdapter = None
    Retry = None


class FyersAdapter:
    """Fyers adapter with OAuth/token validation, retries and duplicate-order safety."""

    def __init__(self):
        self.logger = logging.getLogger("fyers_adapter")
        self.client_id = os.getenv("FYERS_CLIENT_ID", "")
        self.secret_key = os.getenv("FYERS_SECRET_KEY", "")
        self.redirect_uri = os.getenv("FYERS_REDIRECT_URI", "")
        self.access_token = os.getenv("FYERS_ACCESS_TOKEN", "")
        self.base_url = os.getenv("FYERS_BASE_URL", "https://api-t1.fyers.in")

        if requests is None:
            self.session = None
        else:
            self.session = requests.Session()
            retries = Retry(
                total=5,
                backoff_factor=0.5,
                status_forcelist=[429, 500, 502, 503, 504],
                allowed_methods=["GET", "POST"],
            )
            self.session.mount("https://", HTTPAdapter(max_retries=retries))
        self._order_dedupe = set()

    def _require_http_client(self) -> None:
        if self.session is None:
            raise RuntimeError("requests dependency is required for Fyers API calls. Install via requirements.txt")

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"{self.client_id}:{self.access_token}",
            "Content-Type": "application/json",
        }

    def _require_oauth_config(self) -> None:
        if not self.client_id or not self.secret_key or not self.redirect_uri:
            raise ValueError("Missing FYERS_CLIENT_ID/FYERS_SECRET_KEY/FYERS_REDIRECT_URI in environment")

    def _app_id_hash(self) -> str:
        self._require_oauth_config()
        return hashlib.sha256(f"{self.client_id}:{self.secret_key}".encode()).hexdigest()

    def get_login_url(self, state: str = "bot") -> str:
        self._require_oauth_config()
        return (
            "https://api-t1.fyers.in/api/v3/generate-authcode"
            f"?client_id={self.client_id}&redirect_uri={self.redirect_uri}&response_type=code&state={state}"
        )

    def exchange_auth_code(self, auth_code: str) -> Dict:
        self._require_http_client()
        payload = {
            "grant_type": "authorization_code",
            "appIdHash": self._app_id_hash(),
            "code": auth_code,
        }
        resp = self.session.post(f"{self.base_url}/api/v3/token", json=payload, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        token = data.get("access_token")
        if token:
            self.access_token = token
        return data

    def persist_access_token(self, env_path: str = ".env") -> bool:
        """Persist token to .env so restarts keep LIVE auth."""
        if not self.access_token:
            return False

        path = Path(env_path)
        lines = path.read_text().splitlines() if path.exists() else []
        key = "FYERS_ACCESS_TOKEN"
        replaced = False
        new_lines = []
        for line in lines:
            if line.startswith(f"{key}="):
                new_lines.append(f"{key}={self.access_token}")
                replaced = True
            else:
                new_lines.append(line)
        if not replaced:
            new_lines.append(f"{key}={self.access_token}")
        path.write_text("\n".join(new_lines) + "\n")
        return True

    def validate_token(self) -> bool:
        if not self.access_token or not self.client_id:
            return False
        self._require_http_client()
        try:
            resp = self.session.get(
                f"{self.base_url}/api/v3/profile", headers=self._headers(), timeout=10
            )
            if resp.status_code == 200:
                return True
            self.logger.warning("Token validation failed status=%s body=%s", resp.status_code, resp.text)
            return False
        except Exception as exc:
            self.logger.error("Token validation error: %s", exc)
            return False

    def get_ltp(self, symbol: str) -> float:
        self._require_http_client()
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

    def get_history(
        self,
        symbol: str,
        resolution: str = "5",
        range_from: str = "1704067200",
        range_to: str = "1706745600",
    ) -> List[List[float]]:
        self._require_http_client()
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
        self._require_http_client()
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
        self._require_http_client()
        resp = self.session.get(
            f"{self.base_url}/api/v3/positions", headers=self._headers(), timeout=10
        )
        resp.raise_for_status()
        return resp.json().get("netPositions", [])
