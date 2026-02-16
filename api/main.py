from __future__ import annotations

import logging
from pathlib import Path
from typing import Literal, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from engine.mode import TradingMode
from engine.trading_engine import TradingEngine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[logging.FileHandler("logs/trades.log"), logging.StreamHandler()],
)

app = FastAPI(title="Dual Mode Trading System")
engine = TradingEngine()


class ModeSwitchRequest(BaseModel):
    mode: Literal["PAPER", "LIVE"]
    confirm_live: Optional[bool] = False


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
    }
