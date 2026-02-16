from __future__ import annotations

import json
import logging
from pathlib import Path
import threading
from typing import Literal, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from engine.mode import TradingMode
from engine.trading_engine import TradingEngine


class JsonLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        try:
            parsed = json.loads(record.getMessage())
            if isinstance(parsed, dict) and "timestamp" in parsed:
                return json.dumps(parsed)
        except json.JSONDecodeError:
            pass
        return json.dumps(
            {
                "timestamp": self.formatTime(record),
                "event": "log",
                "mode": None,
                "trade_id": None,
                "details": {"logger": record.name, "level": record.levelname, "message": record.getMessage()},
            }
        )


def configure_logging() -> None:
    root = logging.getLogger()
    if root.handlers:
        return
    root.setLevel(logging.INFO)
    formatter = JsonLogFormatter()
    file_handler = logging.FileHandler("logs/trades.log")
    file_handler.setFormatter(formatter)
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    root.addHandler(file_handler)
    root.addHandler(stream_handler)


configure_logging()
app = FastAPI(title="Dual Mode Trading System")
engine = TradingEngine()


class ModeSwitchRequest(BaseModel):
    mode: Literal["PAPER", "LIVE"]
    confirm_live: Optional[bool] = False


@app.on_event("startup")
def startup() -> None:
    Path("logs").mkdir(parents=True, exist_ok=True)
    engine.start()


@app.on_event("shutdown")
def shutdown() -> None:
    engine.stop()


@app.get("/")
def index():
    return FileResponse(Path("ui/index.html"))


@app.get("/signal")
def get_signal():
    return engine.evaluate_market()


@app.post("/approve")
def approve():
    return engine.approve_pending_signal()


@app.post("/reject")
def reject():
    return engine.reject_pending_signal()


@app.post("/stop")
def emergency_stop():
    return engine.emergency_stop()


@app.get("/status")
def status():
    return engine.status()


@app.get("/pnl")
def pnl():
    stats = engine.portfolio.stats()
    return {
        "today_pnl": stats["realized_pnl"],
        "drawdown": stats["max_drawdown"],
        "win_rate": stats["win_rate"],
    }


@app.get("/mode")
def get_mode():
    return {"mode": engine.mode_manager.mode.value}


@app.post("/mode/switch")
def switch_mode(payload: ModeSwitchRequest):
    try:
        return engine.switch_mode(TradingMode(payload.mode), bool(payload.confirm_live))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/trades")
def trades():
    return {"trades": engine.portfolio.trades_snapshot()}


@app.get("/health")
def health():
    fyers_ok = engine.fyers.validate_token() if engine.mode_manager.mode == TradingMode.LIVE else True
    return {
        "status": "ok",
        "mode": engine.mode_manager.mode.value,
        "fyers_auth_valid": fyers_ok,
        "open_position": engine.portfolio.has_open_position(),
        "engine_running": engine.status()["bot_status"] == "RUNNING",
    }


@app.get("/auth/status")
def auth_status():
    return {"authenticated": engine.fyers.validate_token()}


_auth_lock = threading.Lock()


@app.post("/auth/login")
def auth_login():
    with _auth_lock:
        ok = engine.fyers.authenticate_interactive()
    return {"authenticated": ok}
