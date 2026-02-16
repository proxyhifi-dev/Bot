from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
import uvicorn

from api.main import configure_logging
from execution.fyers_adapter import FyersAdapter


def main() -> None:
    load_dotenv()
    Path("logs").mkdir(parents=True, exist_ok=True)
    Path(".secrets").mkdir(parents=True, exist_ok=True)
    configure_logging()

    fyers = FyersAdapter()
    fyers.ensure_authenticated(interactive=True)

    host = os.getenv("APP_HOST", "0.0.0.0")
    port = int(os.getenv("APP_PORT", "8000"))

    print(f"\n✅ Fyers authentication is valid. Starting server at http://{host}:{port}\n")
    uvicorn.run("api.main:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    main()
