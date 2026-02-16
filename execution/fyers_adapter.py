from __future__ import annotations

import hashlib
import json
import logging
import os
from pathlib import Path
import threading
import time
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, urlparse

import requests


class FyersAdapter:
    """Fyers adapter with interactive OAuth, token persistence and resilient HTTP handling."""

    def __init__(self):
        self.logger = logging.getLogger("fyers_adapter")
        self.client_id = os.getenv("FYERS_CLIENT_ID", "").strip()
        self.secret_key = os.getenv("FYERS_SECRET_KEY", "").strip()
        self.redirect_uri = os.getenv("FYERS_REDIRECT_URI", "").strip()
        self.base_url = os.getenv("FYERS_BASE_URL", "https://api-t1.fyers.in").strip()
        token_path = os.getenv("FYERS_TOKEN_FILE", ".secrets/fyers_token.json")
        self.token_file = Path(token_path)

        self.session = requests.Session()
        self.access_token = ""
        self._auth_lock = threading.Lock()
        self._order_dedupe = set()
        self._order_dedupe_lock = threading.Lock()

        self._max_retries = int(os.getenv("FYERS_MAX_RETRIES", "5"))
        self._base_backoff = float(os.getenv("FYERS_BACKOFF_BASE", "0.5"))

        self._load_saved_token()

    def _log_event(self, event: str, details: Dict[str, Any], level: int = logging.INFO) -> None:
        payload = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "event": event,
            "mode": "AUTH",
            "trade_id": None,
            "details": details,
        }
        self.logger.log(level, json.dumps(payload, default=str))

    def _validate_env(self) -> None:
        missing = []
        if not self.client_id:
            missing.append("FYERS_CLIENT_ID")
        if not self.secret_key:
            missing.append("FYERS_SECRET_KEY")
        if not self.redirect_uri:
            missing.append("FYERS_REDIRECT_URI")
        if missing:
            raise RuntimeError(f"Missing required environment values: {', '.join(missing)}")

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"{self.client_id}:{self.access_token}",
            "Content-Type": "application/json",
        }

    def _app_id_hash(self) -> str:
        raw = f"{self.client_id}:{self.secret_key}".encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    def _load_saved_token(self) -> None:
        if not self.token_file.exists():
            return
        try:
            data = json.loads(self.token_file.read_text(encoding="utf-8"))
            token = str(data.get("access_token", "")).strip()
            if token:
                self.access_token = token
                self._log_event("auth_token_loaded", {"token_file": str(self.token_file)})
        except Exception as exc:  # noqa: BLE001
            self._log_event("auth_token_load_failed", {"error": str(exc)}, level=logging.WARNING)

    def _save_token(self, token: str) -> None:
        self.token_file.parent.mkdir(parents=True, exist_ok=True)
        self.token_file.write_text(json.dumps({"access_token": token}, indent=2), encoding="utf-8")
        try:
            os.chmod(self.token_file, 0o600)
        except OSError:
            pass
        self._log_event("auth_token_saved", {"token_file": str(self.token_file)})

    def _extract_auth_code(self, redirected_value: str) -> str:
        v = redirected_value.strip()
        if "http" in v:
            parsed = urlparse(v)
            q = parse_qs(parsed.query)
            code = q.get("auth_code", [""])[0] or q.get("code", [""])[0]
            if code:
                return code
        return v

    def _request_with_backoff(
        self,
        method: str,
        path: str,
        *,
        retry_auth: bool = True,
        **kwargs: Any,
    ) -> requests.Response:
        url = f"{self.base_url}{path}"
        last_exc: Optional[Exception] = None

        for attempt in range(self._max_retries + 1):
            try:
                response = self.session.request(method=method, url=url, timeout=12, **kwargs)
                if response.status_code == 401 and retry_auth:
                    self._log_event("auth_unauthorized", {"path": path, "attempt": attempt + 1}, level=logging.WARNING)
                    if self.ensure_authenticated(interactive=False):
                        kwargs["headers"] = self._headers()
                        continue

                if response.status_code == 429:
                    backoff = self._base_backoff * (2**attempt)
                    self._log_event(
                        "rate_limit",
                        {
                            "method": method,
                            "path": path,
                            "status": 429,
                            "attempt": attempt + 1,
                            "backoff_seconds": backoff,
                        },
                        level=logging.WARNING,
                    )
                    if attempt >= self._max_retries:
                        response.raise_for_status()
                    time.sleep(backoff)
                    continue

                if 500 <= response.status_code < 600 and attempt < self._max_retries:
                    backoff = self._base_backoff * (2**attempt)
                    self._log_event(
                        "server_retry",
                        {
                            "method": method,
                            "path": path,
                            "status": response.status_code,
                            "attempt": attempt + 1,
                            "backoff_seconds": backoff,
                        },
                        level=logging.WARNING,
                    )
                    time.sleep(backoff)
                    continue

                response.raise_for_status()
                return response
            except requests.RequestException as exc:
                last_exc = exc
                if attempt >= self._max_retries:
                    break
                backoff = self._base_backoff * (2**attempt)
                self._log_event(
                    "network_retry",
                    {
                        "method": method,
                        "path": path,
                        "attempt": attempt + 1,
                        "backoff_seconds": backoff,
                        "error": str(exc),
                    },
                    level=logging.WARNING,
                )
                time.sleep(backoff)

        if last_exc:
            raise last_exc
        raise RuntimeError(f"Request failed for {method} {path}")

    def get_login_url(self, state: str = "bot") -> str:
        self._validate_env()
        return (
            "https://api-t1.fyers.in/api/v3/generate-authcode"
            f"?client_id={self.client_id}&redirect_uri={self.redirect_uri}&response_type=code&state={state}"
        )

    def exchange_auth_code(self, auth_code: str) -> Dict[str, Any]:
        self._validate_env()
        payload = {
            "grant_type": "authorization_code",
            "appIdHash": self._app_id_hash(),
            "code": auth_code,
        }
        resp = self._request_with_backoff("POST", "/api/v3/token", json=payload, retry_auth=False)
        data = resp.json()
        token = data.get("access_token")
        if not token:
            raise RuntimeError(f"OAuth exchange failed: {data}")
        self.access_token = str(token)
        self._save_token(self.access_token)
        self._log_event("auth_token_exchanged", {"status": "success"})
        return data

    def authenticate_interactive(self) -> bool:
        with self._auth_lock:
            if self.validate_token():
                return True

            login_url = self.get_login_url(state="manual_login")
            print("\n=== FYERS MANUAL LOGIN REQUIRED ===")
            print("1) Open this URL in your browser and login manually:")
            print(login_url)
            print("2) After login, copy the full redirected URL or auth code and paste below.")
            redirected = input("Auth callback URL / auth code: ").strip()
            if not redirected:
                raise RuntimeError("No auth code provided")

            auth_code = self._extract_auth_code(redirected)
            self.exchange_auth_code(auth_code)
            ok = self.validate_token()
            self._log_event("auth_manual_completed", {"valid": ok})
            if not ok:
                raise RuntimeError("Token validation failed after OAuth login")
            return True

    def ensure_authenticated(self, interactive: bool = False) -> bool:
        if self.validate_token():
            return True
        if interactive:
            return self.authenticate_interactive()
        return False

    def validate_token(self) -> bool:
        if not self.access_token or not self.client_id:
            return False
        try:
            resp = self._request_with_backoff(
                "GET",
                "/api/v3/profile",
                headers=self._headers(),
                retry_auth=False,
            )
            is_valid = resp.status_code == 200
            self._log_event("auth_token_validated", {"valid": is_valid})
            return is_valid
        except requests.RequestException as exc:
            self._log_event("auth_token_invalid", {"error": str(exc)}, level=logging.WARNING)
            return False

    def get_ltp(self, symbol: str) -> float:
        resp = self._request_with_backoff(
            "GET",
            "/data/quotes",
            params={"symbols": symbol},
            headers=self._headers(),
        )
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
        return resp.json().get("candles", [])

    def place_order(self, order: Dict[str, Any]) -> Dict[str, Any]:
        dedupe_key = f"{order.get('symbol')}|{order.get('side')}|{order.get('qty')}|{order.get('type')}"
        with self._order_dedupe_lock:
            if dedupe_key in self._order_dedupe:
                raise ValueError("Duplicate order blocked")
            self._order_dedupe.add(dedupe_key)

        try:
            resp = self._request_with_backoff("POST", "/api/v3/orders", json=order, headers=self._headers())
            data = resp.json()
            self._log_event("order_placed", {"order": order, "response": data})
            return data
        except Exception:
            with self._order_dedupe_lock:
                self._order_dedupe.discard(dedupe_key)
            raise

    def get_positions(self) -> List[Dict[str, Any]]:
        resp = self._request_with_backoff("GET", "/api/v3/positions", headers=self._headers())
        data = resp.json()
        return data.get("netPositions", [])
