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

from dotenv import load_dotenv
import requests


class FyersAdapter:
    """Fyers adapter with interactive OAuth, token persistence and resilient HTTP handling."""

    def __init__(self):
        load_dotenv()
        self.logger = logging.getLogger("fyers_adapter")
        self.client_id = os.getenv("FYERS_CLIENT_ID", "").strip()
        self.secret_key = os.getenv("FYERS_SECRET_KEY", "").strip()
        self.redirect_uri = os.getenv("FYERS_REDIRECT_URI", "").strip()
        self.base_url = os.getenv("FYERS_BASE_URL", "").strip().rstrip("/")
        self.app_type = os.getenv("FYERS_APP_TYPE", "production").strip().lower()
        token_path = os.getenv("FYERS_TOKEN_FILE", ".secrets/fyers_token.json")
        self.token_file = Path(token_path)
        self.access_token = ""
        self._auth_lock = threading.Lock()
        self._auth_fail_lock = threading.Lock()
        self._last_auth_failure_ts = 0.0
        self._auth_failure_cooldown_seconds = int(os.getenv("FYERS_AUTH_FAILURE_COOLDOWN_SECONDS", "30"))

        self.session = requests.Session()

        self._order_dedupe = set()
        self._order_dedupe_lock = threading.Lock()
        self._max_retries = 5
        self._base_backoff = 0.5
        self._validated_env = False
        self._validate_env_once()
        self._load_token()

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"{self.client_id}:{self.access_token}",
            "Content-Type": "application/json",
        }

    def _request_with_backoff(self, method: str, path: str, **kwargs) -> requests.Response:
        self._validate_env_once()
        url = f"{self.base_url}{path}"
        last_exc: Optional[Exception] = None
        for attempt in range(self._max_retries + 1):
            try:
                resp = self.session.request(method=method, url=url, timeout=10, **kwargs)
                if resp.status_code in (429, 503):
                    if attempt >= self._max_retries:
                        self.logger.error(
                            "retry_exhausted method=%s path=%s status=%s attempts=%s",
                            method,
                            path,
                            resp.status_code,
                            attempt + 1,
                        )
                        resp.raise_for_status()
                    backoff = self._base_backoff * (2**attempt)
                    self.logger.warning(
                        "retryable_status method=%s path=%s status=%s attempt=%s backoff_s=%.2f",
                        method,
                        path,
                        resp.status_code,
                        attempt + 1,
                        backoff,
                    )
                    time.sleep(backoff)
                    continue
                if resp.status_code >= 400:
                    resp.raise_for_status()
                return resp
            except requests.RequestException as exc:
                last_exc = exc
                status = getattr(getattr(exc, "response", None), "status_code", None)
                if status in (429, 503):
                    if attempt >= self._max_retries:
                        break
                    backoff = self._base_backoff * (2**attempt)
                    self.logger.warning(
                        "retryable_exception method=%s path=%s status=%s attempt=%s backoff_s=%.2f",
                        method,
                        path,
                        status,
                        attempt + 1,
                        backoff,
                    )
                    time.sleep(backoff)
                    continue
                if status is not None and 400 <= status < 500:
                    break
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
        self._validate_env_once()
        return (
            f"{self.base_url}/api/v3/generate-authcode"
            f"?client_id={self.client_id}&redirect_uri={self.redirect_uri}&response_type=code&state={state}"
        )

    def exchange_auth_code(self, auth_code: str) -> Dict[str, Any]:
        self._validate_env_once()
        if not auth_code:
            raise ValueError("Auth code cannot be empty")
        payload = {
            "grant_type": "authorization_code",
            "appIdHash": self._app_id_hash(),
            "code": auth_code,
        }
        try:
            resp = self._request_with_backoff("POST", "/api/v3/token", json=payload)
        except requests.HTTPError as exc:
            status = getattr(getattr(exc, "response", None), "status_code", None)
            if status == 503:
                cooldown = min(self._auth_failure_cooldown_seconds, 5)
                self.logger.warning("auth_exchange_service_unavailable cooldown_s=%s", cooldown)
                time.sleep(cooldown)
            raise
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
            if not self._can_attempt_authentication():
                remaining = int(self._auth_failure_cooldown_seconds - (time.time() - self._last_auth_failure_ts))
                raise RuntimeError(f"Authentication cooldown active. Retry in ~{max(remaining, 1)}s")

            login_url = self.get_login_url(state="manual_login")
            print("\n=== FYERS MANUAL LOGIN REQUIRED ===")
            print("1) Open this URL in your browser and login manually:")
            print(login_url)
            print("2) After login, copy the full redirected URL or auth code and paste below.")
            redirected = input("Auth callback URL / auth code: ").strip()
            if not redirected:
                raise RuntimeError("No auth code provided")

            auth_code = self._extract_auth_code(redirected)
            try:
                self.exchange_auth_code(auth_code)
                ok = self.validate_token()
                self._log_event("auth_manual_completed", {"valid": ok})
                if not ok:
                    self._mark_auth_failure()
                    raise RuntimeError("Token validation failed after OAuth login")
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

    def validate_token(self) -> bool:
        self._validate_env_once()
        if not self.access_token or not self.client_id:
            return False
        try:
            resp = self._request_with_backoff("GET", "/api/v3/profile", headers=self._headers())
            if resp.status_code == 200:
                return True
            self.logger.warning("Token validation failed status=%s", resp.status_code)
            return False
        except requests.RequestException as exc:
            self._log_event("auth_token_invalid", {"error": str(exc)}, level=logging.WARNING)
            return False

    def get_ltp(self, symbol: str) -> float:
        if not symbol:
            raise ValueError("Symbol is required")
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

    def place_order(self, order: Dict[str, Any]) -> Dict[str, Any]:
        self._validate_order(order)
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

    def _validate_env_once(self) -> None:
        if self._validated_env:
            return
        self._validate_env()
        self._validated_env = True

    def _validate_env(self) -> None:
        required = {
            "FYERS_CLIENT_ID": self.client_id,
            "FYERS_SECRET_KEY": self.secret_key,
            "FYERS_REDIRECT_URI": self.redirect_uri,
            "FYERS_BASE_URL": self.base_url,
        }
        missing = [k for k, v in required.items() if not v]
        if missing:
            raise RuntimeError(f"Missing required environment variables: {', '.join(missing)}")

        parsed_base = urlparse(self.base_url)
        if parsed_base.scheme not in {"http", "https"} or not parsed_base.netloc:
            raise RuntimeError("FYERS_BASE_URL must be a valid absolute URL")

        parsed_redirect = urlparse(self.redirect_uri)
        if parsed_redirect.scheme not in {"http", "https"} or not parsed_redirect.netloc:
            raise RuntimeError("FYERS_REDIRECT_URI must be a valid absolute URL")

        host = parsed_base.netloc.lower()
        if "api-t1" in host and self.app_type == "production":
            self.logger.warning("env_mismatch base_url=%s app_type=%s", self.base_url, self.app_type)
        if "api-t1" not in host and self.app_type in {"test", "sandbox"}:
            self.logger.warning("env_mismatch base_url=%s app_type=%s", self.base_url, self.app_type)

    def _validate_order(self, order: Dict[str, Any]) -> None:
        symbol = str(order.get("symbol", "")).strip()
        qty = order.get("qty")
        product_type = order.get("productType")
        side = order.get("side")
        order_type = order.get("type")

        if not symbol:
            raise ValueError("Order validation failed: symbol is required")
        if not isinstance(qty, int) or qty <= 0:
            raise ValueError("Order validation failed: qty must be a positive integer")
        if product_type != "INTRADAY":
            raise ValueError("Order validation failed: productType must be INTRADAY")
        if side not in (1, -1):
            raise ValueError("Order validation failed: side must be 1 or -1")
        if order_type not in (1, 2, 3, 4):
            raise ValueError("Order validation failed: unsupported type")

    def _app_id_hash(self) -> str:
        raw = f"{self.client_id}:{self.secret_key}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def _save_token(self, token: str) -> None:
        self.token_file.parent.mkdir(parents=True, exist_ok=True)
        payload = {"access_token": token, "saved_at": int(time.time())}
        self.token_file.write_text(json.dumps(payload), encoding="utf-8")
        os.chmod(self.token_file, 0o600)

    def _load_token(self) -> None:
        if not self.token_file.exists():
            return
        try:
            data = json.loads(self.token_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            self.logger.warning("token_file_read_failed path=%s error=%s", self.token_file, exc)
            self._recover_corrupted_token_file()
            return
        token = str(data.get("access_token", "")).strip()
        if token:
            self.access_token = token
        else:
            self.logger.warning("token_file_missing_access_token path=%s", self.token_file)

    def _recover_corrupted_token_file(self) -> None:
        try:
            backup = self.token_file.with_suffix(f"{self.token_file.suffix}.corrupt")
            self.token_file.replace(backup)
            self.logger.warning("token_file_quarantined path=%s backup=%s", self.token_file, backup)
        except OSError as exc:
            self.logger.warning("token_file_recovery_failed path=%s error=%s", self.token_file, exc)

    @staticmethod
    def _extract_auth_code(redirected_or_code: str) -> str:
        value = redirected_or_code.strip()
        if value.startswith("http://") or value.startswith("https://"):
            parsed = urlparse(value)
            code = parse_qs(parsed.query).get("code", [""])[0]
            if not code:
                raise ValueError("No auth code in callback URL")
            return code
        return value

    def _log_event(self, event: str, details: Dict[str, Any], level: int = logging.INFO) -> None:
        redacted = dict(details)
        if "access_token" in redacted:
            redacted["access_token"] = "***"
        self.logger.log(level, "event=%s details=%s", event, redacted)

    def _can_attempt_authentication(self) -> bool:
        with self._auth_fail_lock:
            return (time.time() - self._last_auth_failure_ts) >= self._auth_failure_cooldown_seconds

    def _mark_auth_failure(self) -> None:
        with self._auth_fail_lock:
            self._last_auth_failure_ts = time.time()
