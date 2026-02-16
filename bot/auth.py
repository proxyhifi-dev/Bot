import json
import logging
import secrets
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import parse_qs, urlencode, urlparse

import requests

from health import check_api_health
from utils import FyersConfig, compute_backoff, sleep_with_log


class FyersAuthManager:
    def __init__(self, config: FyersConfig, logger: logging.Logger):
        self.config = config
        self.logger = logger

    def generate_auth_url(self, state: Optional[str] = None) -> str:
        state = state or secrets.token_urlsafe(16)
        params = {
            "client_id": self.config.client_id,
            "redirect_uri": self.config.redirect_uri,
            "response_type": "code",
            "state": state,
        }
        return f"{self.config.base_url}/api/v3/generate-authcode?{urlencode(params)}"

    @staticmethod
    def extract_auth_code(input_value: str) -> str:
        value = input_value.strip()
        if value.startswith("http://") or value.startswith("https://"):
            parsed = urlparse(value)
            code = parse_qs(parsed.query).get("code", [""])[0]
            if not code:
                raise ValueError("No 'code' query parameter found in redirect URL.")
            return code
        return value

    def exchange_code_for_token(self, auth_code: str) -> Dict[str, Any]:
        health = check_api_health(self.config, self.logger)
        if not health.healthy:
            raise RuntimeError(f"Skipping OAuth because API is unhealthy: {health.message}")

        payload = {
            "client_id": self.config.client_id,
            "secret_key": self.config.secret_key,
            "grant_type": "authorization_code",
            "code": auth_code,
            "redirect_uri": self.config.redirect_uri,
        }
        token_url = f"{self.config.base_url}/api/v3/token"

        for attempt in range(1, self.config.max_retries + 1):
            try:
                response = requests.post(token_url, json=payload, timeout=self.config.timeout_seconds)
                if response.status_code in (429, 502, 503):
                    delay = compute_backoff(self.config.backoff_base, attempt)
                    sleep_with_log(
                        self.logger,
                        f"Token exchange retry for status {response.status_code}",
                        delay,
                    )
                    continue
                response.raise_for_status()
                data = response.json()
                access_token = data.get("access_token")
                if not access_token:
                    raise RuntimeError(f"Token response did not include access_token: {data}")
                self.save_token(data)
                return data
            except requests.RequestException as exc:
                if attempt == self.config.max_retries:
                    raise RuntimeError(f"Token exchange failed after retries: {exc}") from exc
                delay = compute_backoff(self.config.backoff_base, attempt)
                sleep_with_log(self.logger, "Token exchange request error", delay)

        raise RuntimeError("Token exchange failed due to repeated gateway/rate-limit errors.")

    def save_token(self, token_payload: Dict[str, Any]) -> None:
        self.config.token_file.parent.mkdir(parents=True, exist_ok=True)
        self.config.token_file.write_text(json.dumps(token_payload, indent=2), encoding="utf-8")
        self.logger.info(
            "Token persisted",
            extra={"details": {"path": str(self.config.token_file)}},
        )

    def load_token(self) -> Optional[Dict[str, Any]]:
        path: Path = self.config.token_file
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            self.logger.error(
                "Failed to read token file",
                extra={"details": {"path": str(path), "error": str(exc)}},
            )
            return None

    def validate_token(self, access_token: str) -> bool:
        profile_url = f"{self.config.base_url}/api/v3/profile"
        headers = {"Authorization": f"{self.config.client_id}:{access_token}"}

        for attempt in range(1, self.config.max_retries + 1):
            try:
                response = requests.get(profile_url, headers=headers, timeout=self.config.timeout_seconds)
                if response.status_code == 200:
                    return True
                if response.status_code in (429, 502, 503):
                    delay = compute_backoff(self.config.backoff_base, attempt)
                    sleep_with_log(
                        self.logger,
                        f"Token validation retry for status {response.status_code}",
                        delay,
                    )
                    continue
                return False
            except requests.RequestException as exc:
                if attempt == self.config.max_retries:
                    self.logger.error(
                        "Token validation failed",
                        extra={"details": {"error": str(exc)}},
                    )
                    return False
                delay = compute_backoff(self.config.backoff_base, attempt)
                sleep_with_log(self.logger, "Token validation request error", delay)
        return False

    def get_valid_access_token(self) -> str:
        token_payload = self.load_token()
        if token_payload:
            token = token_payload.get("access_token", "")
            if token and self.validate_token(token):
                self.logger.info("Using existing valid token", extra={"details": {}})
                return token

        login_url = self.generate_auth_url()
        print("\nOpen the following URL and complete login manually:\n")
        print(login_url)
        redirect_input = input("\nPaste redirect URL (or auth code): ").strip()
        auth_code = self.extract_auth_code(redirect_input)
        payload = self.exchange_code_for_token(auth_code)
        token = payload.get("access_token", "")
        if not token or not self.validate_token(token):
            raise RuntimeError("Received token is invalid. Please retry login.")
        self.logger.info("Manual OAuth completed", extra={"details": {}})
        return token
