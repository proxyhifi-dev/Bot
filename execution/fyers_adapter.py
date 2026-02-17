from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import os
import struct
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
        self.fyers_user_id = os.getenv("FYERS_USER_ID", "").strip()
        self.fyers_pin = os.getenv("FYERS_PIN", "").strip()
        self.fyers_totp_secret = os.getenv("FYERS_TOTP_SECRET", "").strip()
        self.enable_auto_auth = os.getenv("FYERS_AUTO_AUTH", "false").strip().lower() == "true"

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

        base_payload = {
            "grant_type": "authorization_code",
            "appIdHash": self._app_id_hash(),
        }

        # FYERS token APIs have used both `code` and `auth_code` keys depending
        # on gateway/versioning. Try both to keep login robust across accounts.
        payload_attempts = [
            {**base_payload, "code": auth_code},
            {**base_payload, "auth_code": auth_code},
        ]

        last_error: Optional[Exception] = None
        for payload in payload_attempts:
            try:
                resp = self._request_with_backoff("POST", "/api/v3/token", json=payload)
                data = resp.json()

                token = data.get("access_token")
                if not token:
                    raise RuntimeError(f"OAuth exchange failed: {data}")

                self.access_token = token
                self._save_token(token)
                self.validate_token(force=True)
                return data
            except requests.HTTPError as exc:
                last_error = exc
                status = getattr(getattr(exc, "response", None), "status_code", None)
                # Retry with alternate payload key only for auth-related errors.
                if status not in (400, 401):
                    raise

        if last_error is not None:
            raise last_error
        raise RuntimeError("OAuth exchange failed for all supported payload variants")

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

    def authenticate_auto(self) -> bool:
        with self._auth_lock:
            if self.validate_token():
                return True

            if not self._can_attempt_authentication():
                raise RuntimeError("Authentication cooldown active. Please wait.")

            try:
                auth_code = self._generate_auth_code_auto()
                self.exchange_auth_code(auth_code)
                if not self.validate_token(force=True):
                    self._mark_auth_failure()
                    raise RuntimeError("Auto-auth token validation failed")
                self.logger.info("Auto authentication succeeded")
                return True
            except Exception:
                self._mark_auth_failure()
                raise

    def ensure_authenticated(self, interactive: bool = False) -> bool:
        if self.validate_token():
            return True
        if self.enable_auto_auth:
            self.authenticate_auto()
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
            query = parse_qs(parsed.query)
            # FYERS callback URLs can include both `code` (status code) and
            # `auth_code` (actual authorization code). Prefer auth_code when
            # available to avoid exchanging an HTTP status value like "200".
            return query.get("auth_code", [""])[0] or query.get("code", [""])[0]
        return value.strip()

    def _can_attempt_authentication(self) -> bool:
        with self._auth_fail_lock:
            return (time.time() - self._last_auth_failure_ts) >= self._auth_failure_cooldown_seconds

    def _mark_auth_failure(self) -> None:
        with self._auth_fail_lock:
            self._last_auth_failure_ts = time.time()


    @staticmethod
    def _generate_totp(secret: str, interval: int = 30, digits: int = 6) -> str:
        normalized = secret.strip().replace(" ", "").upper()
        key = base64.b32decode(normalized + "=" * ((8 - len(normalized) % 8) % 8))
        timestep = int(time.time() // interval)
        msg = struct.pack(">Q", timestep)
        digest = hmac.new(key, msg, hashlib.sha1).digest()
        offset = digest[-1] & 0x0F
        code = ((digest[offset] & 0x7F) << 24) | ((digest[offset + 1] & 0xFF) << 16) | ((digest[offset + 2] & 0xFF) << 8) | (digest[offset + 3] & 0xFF)
        return str(code % (10 ** digits)).zfill(digits)

    def _generate_auth_code_auto(self) -> str:
        self._validate_auto_auth_settings()

        otp_request_key = self._send_login_otp()
        verify_otp_request_key = self._verify_totp(otp_request_key)
        pin_access_token = self._verify_pin(verify_otp_request_key)
        return self._request_auth_code(pin_access_token)

    def _validate_auto_auth_settings(self) -> None:
        missing = []
        if not self.fyers_user_id:
            missing.append("FYERS_USER_ID")
        if not self.fyers_pin:
            missing.append("FYERS_PIN")
        if not self.fyers_totp_secret:
            missing.append("FYERS_TOTP_SECRET")
        if missing:
            raise RuntimeError(f"Auto authentication missing env vars: {', '.join(missing)}")

    def _send_login_otp(self) -> str:
        payload = {"fy_id": self.fyers_user_id, "app_id": "2"}
        resp = self.session.post("https://api-t2.fyers.in/vagator/v2/send_login_otp_v2", json=payload, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        request_key = data.get("request_key")
        if not request_key:
            raise RuntimeError(f"Unable to send OTP: {data}")
        return request_key

    def _verify_totp(self, request_key: str) -> str:
        totp = self._generate_totp(self.fyers_totp_secret)
        payload = {"request_key": request_key, "otp": totp}
        resp = self.session.post("https://api-t2.fyers.in/vagator/v2/verify_otp", json=payload, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        verified_request_key = data.get("request_key")
        if not verified_request_key:
            raise RuntimeError(f"Unable to verify TOTP: {data}")
        return verified_request_key

    def _verify_pin(self, request_key: str) -> str:
        payload = {"request_key": request_key, "identity_type": "pin", "identifier": self.fyers_pin}
        resp = self.session.post("https://api-t2.fyers.in/vagator/v2/verify_pin_v2", json=payload, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        access_token = data.get("data", {}).get("access_token")
        if not access_token:
            raise RuntimeError(f"Unable to verify pin: {data}")
        return access_token

    def _request_auth_code(self, pin_access_token: str) -> str:
        payload = {
            "fyers_id": self.fyers_user_id,
            "app_id": self.client_id.split("-")[0],
            "redirect_uri": self.redirect_uri,
            "appType": "100",
            "code_challenge": "",
            "state": "auto_auth",
            "scope": "",
            "nonce": "",
            "response_type": "code",
            "create_cookie": True,
        }
        headers = {"Authorization": f"Bearer {pin_access_token}"}
        resp = self.session.post("https://api.fyers.in/api/v2/token", json=payload, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        redirect_url = data.get("Url") or data.get("url")
        if not redirect_url:
            raise RuntimeError(f"Unable to fetch auth code URL: {data}")
        auth_code = self._extract_auth_code(redirect_url)
        if not auth_code:
            raise RuntimeError(f"Auth code missing in redirect URL: {redirect_url}")
        return auth_code
