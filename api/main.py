from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Literal, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
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
    Path("logs").mkdir(parents=True, exist_ok=True)
    file_handler = logging.FileHandler("logs/trades.log")
    file_handler.setFormatter(formatter)
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    root.addHandler(file_handler)
    root.addHandler(stream_handler)


configure_logging()
app = FastAPI(title="Dual Mode Trading System")


class ModeSwitchRequest(BaseModel):
    mode: Literal["PAPER", "LIVE"]
    confirm_live: Optional[bool] = False


class AuthExchangeRequest(BaseModel):
    auth_code: str


def get_engine(request: Request) -> TradingEngine:
    engine: Optional[TradingEngine] = getattr(request.app.state, "engine", None)
    if engine is None:
        raise HTTPException(status_code=503, detail="Engine unavailable")
    return engine


@app.on_event("startup")
def startup() -> None:
    load_dotenv()
    Path("logs").mkdir(parents=True, exist_ok=True)
    Path(".secrets").mkdir(parents=True, exist_ok=True)
    app.state.engine = TradingEngine()
    app.state.engine.start()


@app.on_event("shutdown")
def shutdown() -> None:
    engine = getattr(app.state, "engine", None)
    if engine:
        engine.stop()


@app.get("/")
def index():
    return FileResponse(Path("ui/index.html"))


@app.get("/signal")
def get_signal(request: Request):
    engine = get_engine(request)
    if engine.is_running:
        return engine.latest_evaluation()
    return engine.evaluate_market()


@app.post("/approve")
def approve(request: Request):
    return get_engine(request).approve_pending_signal()


@app.post("/reject")
def reject(request: Request):
    return get_engine(request).reject_pending_signal()


@app.post("/stop")
def emergency_stop(request: Request):
    return get_engine(request).emergency_stop()


@app.get("/status")
def status(request: Request):
    return get_engine(request).status()


@app.get("/pnl")
def pnl(request: Request):
    stats = get_engine(request).portfolio.stats()
    return {
        "today_pnl": stats["realized_pnl"],
        "drawdown": stats["max_drawdown"],
        "win_rate": stats["win_rate"],
    }


@app.get("/mode")
def get_mode(request: Request):
    engine = get_engine(request)
    return {"mode": engine.mode_manager.mode.value}


@app.post("/mode/switch")
def switch_mode(payload: ModeSwitchRequest, request: Request):
    engine = get_engine(request)
    try:
        return engine.switch_mode(TradingMode(payload.mode), bool(payload.confirm_live))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/trades")
def trades(request: Request):
    return {"trades": get_engine(request).portfolio.trades_snapshot()}


@app.get("/health")
def health(request: Request):
    engine = get_engine(request)
    fyers_ok = engine.fyers.validate_token() if engine.mode_manager.mode == TradingMode.LIVE else True
    return {
        "status": "ok",
        "mode": engine.mode_manager.mode.value,
        "fyers_auth_valid": fyers_ok,
        "open_position": engine.portfolio.has_open_position(),
        "engine_running": engine.status()["bot_status"] == "RUNNING",
    }


@app.get("/auth/status")
def auth_status(request: Request):
    return {"authenticated": get_engine(request).fyers.validate_token()}


@app.get("/auth/login-url")
def auth_login_url(request: Request):
    return {"login_url": get_engine(request).fyers.get_login_url()}




@app.post("/auth/login")
def auth_login_deprecated():
    raise HTTPException(
        status_code=410,
        detail="Deprecated. Use GET /auth/login-url and POST /auth/exchange for non-interactive OAuth flow.",
    )
@app.post("/auth/exchange")
def auth_exchange(payload: AuthExchangeRequest, request: Request):
    engine = get_engine(request)
    try:
        engine.fyers.exchange_auth_code(payload.auth_code.strip())
        valid = engine.fyers.validate_token(force=True)
        return {"authenticated": valid}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
