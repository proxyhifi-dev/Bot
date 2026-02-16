import json
import logging
import os
import random
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from dotenv import load_dotenv


@dataclass
class FyersConfig:
    client_id: str
    secret_key: str
    redirect_uri: str
    base_url: str
    token_file: Path
    max_retries: int = 5
    backoff_base: float = 1.0
    timeout_seconds: int = 15


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "event": record.getMessage(),
            "details": getattr(record, "details", {}),
        }
        if record.exc_info:
            payload["details"]["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def setup_logger(log_file: str = "logs/bot.log") -> logging.Logger:
    Path(log_file).parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("fyers_bot")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        handler = logging.FileHandler(log_file)
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)

        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(JsonFormatter())
        logger.addHandler(stream_handler)
    return logger


def load_config() -> FyersConfig:
    load_dotenv()
    required = ["FYERS_CLIENT_ID", "FYERS_SECRET_KEY", "FYERS_REDIRECT_URI", "FYERS_BASE_URL"]
    missing = [name for name in required if not os.getenv(name)]
    if missing:
        raise ValueError(f"Missing required environment keys: {', '.join(missing)}")

    token_file = Path(os.getenv("FYERS_TOKEN_FILE", ".secrets/fyers_token.json"))
    token_file.parent.mkdir(parents=True, exist_ok=True)

    return FyersConfig(
        client_id=os.getenv("FYERS_CLIENT_ID", "").strip(),
        secret_key=os.getenv("FYERS_SECRET_KEY", "").strip(),
        redirect_uri=os.getenv("FYERS_REDIRECT_URI", "").strip(),
        base_url=os.getenv("FYERS_BASE_URL", "").strip().rstrip("/"),
        token_file=token_file,
        max_retries=int(os.getenv("FYERS_MAX_RETRIES", "5")),
        backoff_base=float(os.getenv("FYERS_BACKOFF_BASE", "1.0")),
        timeout_seconds=int(os.getenv("FYERS_HTTP_TIMEOUT", "15")),
    )


def compute_backoff(base_seconds: float, attempt: int, cap: float = 60.0) -> float:
    jitter = random.uniform(0, 0.3 * base_seconds)
    delay = min(cap, (base_seconds * (2 ** max(attempt - 1, 0))) + jitter)
    return delay


def sleep_with_log(logger: logging.Logger, reason: str, seconds: float) -> None:
    logger.warning(
        f"Sleeping for cooldown: {seconds:.2f}s",
        extra={"details": {"reason": reason, "seconds": seconds}},
    )
    time.sleep(seconds)
