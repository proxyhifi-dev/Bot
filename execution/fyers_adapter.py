from __future__ import annotations

import hashlib
import json
import logging
import os
import threading
import time
from pathlib import Path
from typing import Any, Dict, List
from urllib.parse import parse_qs, urlparse

import requests


class FyersAdapter:
    """
    Production-grade Fyers adapter:
    - Manual OAuth
    - Token persistence
    - Strict environment validation
    - No test/prod mixing
    - Retry with backoff
    - Auth cooldown protection
    """

    def __init__(self):
        self.logger = logging.getLogger("fyers_adapter")

        # ----------------------------
        # Environment
        # ----------------------------
        self.client_id = os.getenv("FYERS_CLIENT_ID", "").strip()
        self.secret_key = os.getenv("FYERS_SECRET_KEY", "").strip()
        self.redirect_uri = os.getenv("FYERS_REDIRECT_URI", "").strip()
        self.base_url = os.getenv("FYERS_BASE_URL", "").strip()

        if not self.client_id:
            raise RuntimeError("FYERS_CLIENT_ID not set")
        if not self.secret_key:
            raise RuntimeError("FYERS_SECRET_KEY not set")
        if not self.redirect_uri:
            raise RuntimeError("FYERS_REDIRECT_URI not set")
        if not self.base_url:
            raise RuntimeError("FYERS_BASE_URL not set")

        # No fallback to api-t1 allowed
        if "api-t1" in self.base_url:
            self.logger.warning("Using TEST environment (api-t1). Ensure this is intentional.")

        token_path = os.getenv("FYERS_TOKEN_FILE", ".secrets/fyers_token.json")
        self.token_file = Path(token_path)

        self.session = requests.Session()
        self.access_token = ""

        # ----------------------------
        # Retry Settings
        # ----------------------------
        self._max_retries = int(os.getenv("FYERS_MAX_RETRIES", "5"))
        self._base_backoff = float(os.getenv("FYERS_BACKOFF_BASE", "0.5"))

        # ----------------------------
        # Auth Cooldown
        # ----------------------------
        self._auth_lock = threading.Lock()
        self._token_validation_lock = threading.Lock()
        self._token_validation_ttl_seconds = int(os.getenv("FYERS_TOKEN_VALIDATION_TTL_SECONDS", "15"))
        self._last_token_validation_ts = 0.0
        self._last_token_validation_result = False
        self._auth_fail_lock = threading.Lock()
        self._last_auth_failure_ts = 0.0
        self._auth_failure_cooldown_seconds = int(
            os.getenv("FYERS_AUTH_FAILURE_COOLDOWN_SECONDS", "60")
        )

        # ----------------------------
        # Order Dedupe
        # ----------------------------
        self._order_dedupe = set()
        self._order_dedupe_lock = threading.Lock()

        self._load_token()

    # ============================================================
    # AUTH HEADERS
    # ============================================================

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"{self.client_id}:{self.access_token}",
            "Content-Type": "application/json",
        }

    # ============================================================
    # HTTP WITH BACKOFF
    # ============================================================

    def _request_with_backoff(self, method: str, path: str, **kwargs) -> requests.Response:
        url = f"{self.base_url}{path}"
        last_exc = None

        for attempt in range(self._max_retries + 1):
            try:
                resp = self.session.request(method, url, timeout=15, **kwargs)

                if resp.status_code in (429, 500, 502, 503, 504):
                    if attempt >= self._max_retries:
                        resp.raise_for_status()
                    backoff = self._base_backoff * (2 ** attempt)
                    self.logger.warning(
                        "retryable_status method=%s path=%s status=%s attempt=%s backoff=%.2f",
                        method, path, resp.status_code, attempt + 1, backoff
                    )
                    time.sleep(backoff)
                    continue

                if resp.status_code >= 400:
                    resp.raise_for_status()

                return resp

            except requests.RequestException as exc:
                last_exc = exc
                status = getattr(getattr(exc, "response", None), "status_code", None)

                if status and 400 <= status < 500:
                    break

                if attempt >= self._max_retries:
                    break

                backoff = self._base_backoff * (2 ** attempt)
                time.sleep(backoff)

        if last_exc:
            raise last_exc

        raise RuntimeError(f"Unhandled request failure for {method} {path}")

    # ============================================================
    # OAUTH LOGIN
    # ============================================================

    def get_login_url(self, state: str = "manual_login") -> str:
        return (
            f"{self.base_url}/api/v3/generate-authcode"
            f"?client_id={self.client_id}"
            f"&redirect_uri={self.redirect_uri}"
            "&response_type=code"
            f"&state={state}"
        )

    def exchange_auth_code(self, auth_code: str) -> Dict[str, Any]:
        if not auth_code:
            raise ValueError("Auth code cannot be empty")

        payload = {
            "grant_type": "authorization_code",
            "appIdHash": self._app_id_hash(),
            "code": auth_code,
        }

        resp = self._request_with_backoff("POST", "/api/v3/token", json=payload)
        data = resp.json()

        token = data.get("access_token")
        if not token:
            raise RuntimeError(f"OAuth exchange failed: {data}")

        self.access_token = token
        self._save_token(token)
        self.validate_token(force=True)
        return data

    def authenticate_interactive(self) -> bool:
        with self._auth_lock:
            if self.validate_token():
                return True

            if not self._can_attempt_authentication():
                raise RuntimeError("Authentication cooldown active. Please wait.")

            print("\n=== FYERS LOGIN REQUIRED ===")
            print("Open this URL and login:")
            print(self.get_login_url())

            redirected = input("Paste full callback URL or auth code: ").strip()
            auth_code = self._extract_auth_code(redirected)

            try:
                self.exchange_auth_code(auth_code)
                if not self.validate_token():
                    self._mark_auth_failure()
                    raise RuntimeError("Token validation failed")
                return True
            except Exception:
                self._mark_auth_failure()
                raise

    def ensure_authenticated(self, interactive: bool = False) -> bool:
        if self.validate_token():
            return True
        if interactive:
            return self.authenticate_interactive()
        return False

    def validate_token(self, force: bool = False) -> bool:
        if not self.access_token:
            return False

        with self._token_validation_lock:
            now = time.time()
            if not force and (now - self._last_token_validation_ts) < self._token_validation_ttl_seconds:
                return self._last_token_validation_result

            try:
                resp = self._request_with_backoff("GET", "/api/v3/profile", headers=self._headers())
                valid = resp.status_code == 200
            except Exception:
                valid = False

            self._last_token_validation_ts = now
            self._last_token_validation_result = valid
            return valid

    # ============================================================
    # MARKET DATA
    # ============================================================

    def get_ltp(self, symbol: str) -> float:
        resp = self._request_with_backoff(
            "GET", "/data/quotes",
            params={"symbols": symbol},
            headers=self._headers(),
        )
        data = resp.json()
        return float(data.get("d", [{}])[0].get("v", {}).get("lp"))

    def get_history(self, symbol: str, resolution: str = "5",
                    range_from: str = "1704067200",
                    range_to: str = "1706745600") -> List[List[float]]:

        resp = self._request_with_backoff(
            "GET", "/data/history",
            params={
                "symbol": symbol,
                "resolution": resolution,
                "date_format": "0",
                "range_from": range_from,
                "range_to": range_to,
                "cont_flag": "1",
            },
            headers=self._headers(),
        )
        return resp.json().get("candles", [])

    # ============================================================
    # ORDERS
    # ============================================================

    def place_order(self, order: Dict[str, Any]) -> Dict[str, Any]:
        key = f"{order.get('symbol')}|{order.get('side')}|{order.get('qty')}"
        with self._order_dedupe_lock:
            if key in self._order_dedupe:
                raise ValueError("Duplicate order blocked")
            self._order_dedupe.add(key)

        try:
            resp = self._request_with_backoff(
                "POST", "/api/v3/orders",
                json=order,
                headers=self._headers(),
            )
            return resp.json()
        finally:
            with self._order_dedupe_lock:
                self._order_dedupe.discard(key)

    def get_positions(self) -> List[Dict]:
        resp = self._request_with_backoff(
            "GET", "/api/v3/positions",
            headers=self._headers(),
        )
        return resp.json().get("netPositions", [])

    # ============================================================
    # UTILITIES
    # ============================================================

    def _app_id_hash(self) -> str:
        raw = f"{self.client_id}:{self.secret_key}"
        return hashlib.sha256(raw.encode()).hexdigest()

    def _save_token(self, token: str) -> None:
        self.token_file.parent.mkdir(parents=True, exist_ok=True)
        self.token_file.write_text(json.dumps({
            "access_token": token,
            "saved_at": int(time.time())
        }), encoding="utf-8")
        os.chmod(self.token_file, 0o600)

    def _load_token(self) -> None:
        if not self.token_file.exists():
            return
        try:
            data = json.loads(self.token_file.read_text())
            self.access_token = data.get("access_token", "")
        except Exception:
            pass

    @staticmethod
    def _extract_auth_code(value: str) -> str:
        if value.startswith("http"):
            parsed = urlparse(value)
            return parse_qs(parsed.query).get("code", [""])[0]
        return value.strip()

    def _can_attempt_authentication(self) -> bool:
        with self._auth_fail_lock:
            return (time.time() - self._last_auth_failure_ts) >= self._auth_failure_cooldown_seconds

    def _mark_auth_failure(self) -> None:
        with self._auth_fail_lock:
            self._last_auth_failure_ts = time.time()
