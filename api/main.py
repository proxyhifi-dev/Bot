from __future__ import annotations

import logging
from pathlib import Path
from typing import Literal, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, RedirectResponse
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


@app.get("/auth/login")
def auth_login(state: str = "bot"):
    """Step 1: open Fyers OAuth login URL."""
    try:
        return RedirectResponse(engine.fyers.get_login_url(state=state))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/auth/callback")
def auth_callback(code: str = Query(...), state: str = Query("bot")):
    """Step 2: Fyers redirects here with auth code; we exchange and persist token."""
    try:
        token_resp = engine.fyers.exchange_auth_code(code)
        engine.fyers.persist_access_token(".env")
        return {
            "status": "authenticated",
            "state": state,
            "token_saved": True,
            "token_valid": engine.fyers.validate_token(),
            "message": "Token exchanged and saved to .env as FYERS_ACCESS_TOKEN",
            "raw": {k: v for k, v in token_resp.items() if k != "access_token"},
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"OAuth callback failed: {exc}") from exc


@app.get("/auth/status")
def auth_status():
    return {
        "configured": bool(engine.fyers.client_id and engine.fyers.secret_key and engine.fyers.redirect_uri),
        "has_access_token": bool(engine.fyers.access_token),
        "token_valid": engine.fyers.validate_token(),
    }


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
    return {"trades": engine.portfolio.trades}


@app.get("/health")
def health():
    fyers_ok = engine.fyers.validate_token() if engine.mode_manager.mode == TradingMode.LIVE else True
    return {
        "status": "ok",
        "mode": engine.mode_manager.mode.value,
        "fyers_auth_valid": fyers_ok,
        "open_position": engine.portfolio.has_open_position(),
    }
