from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
import logging
from typing import Dict

from engine.mode import TradingMode, ModeManager
from engine.portfolio import Portfolio
from execution.fyers_adapter import FyersAdapter


class PaperExecutionSimulator:
    def execute_entry(self, portfolio: Portfolio, signal: Dict, ltp: float, mode: TradingMode):
        return portfolio.open_trade(
            symbol=signal["symbol"],
            side=signal["side"],
            qty=signal["qty"],
            entry_price=ltp,
            stop_loss=signal["stop_loss"],
            target=signal["target"],
            mode=mode.value,
        )


class TradeExecutor:
    def __init__(self, mode_manager: ModeManager, portfolio: Portfolio, fyers: FyersAdapter):
        self.mode_manager = mode_manager
        self.portfolio = portfolio
        self.fyers = fyers
        self.paper = PaperExecutionSimulator()
        self.logger = logging.getLogger("execution")

    def enter_trade(self, signal: Dict, ltp: float) -> Dict:
        mode = self.mode_manager.mode
        if mode == TradingMode.PAPER:
            p = self.paper.execute_entry(self.portfolio, signal, ltp, mode)
            self.logger.info("mode=%s action=ENTRY symbol=%s qty=%s price=%s", mode.value, p.symbol, p.qty, ltp)
            return {"status": "filled", "mode": mode.value, "position": asdict(p), "broker": "simulator"}

        if mode == TradingMode.LIVE:
            order = {
                "symbol": signal["symbol"],
                "qty": signal["qty"],
                "type": 2,
                "side": 1 if signal["side"] == "BUY" else -1,
                "productType": "INTRADAY",
            }
            broker_resp = self.fyers.place_order(order)
            p = self.portfolio.open_trade(
                symbol=signal["symbol"],
                side=signal["side"],
                qty=signal["qty"],
                entry_price=ltp,
                stop_loss=signal["stop_loss"],
                target=signal["target"],
                mode=mode.value,
            )
            self.logger.info("mode=%s action=ENTRY symbol=%s qty=%s price=%s", mode.value, p.symbol, p.qty, ltp)
            return {"status": "filled", "mode": mode.value, "position": asdict(p), "broker": broker_resp}

        raise ValueError("Unknown mode")

    def exit_trade(self, ltp: float, reason: str) -> Dict:
        mode = self.mode_manager.mode
        if not self.portfolio.has_open_position():
            return {"status": "no_open_position"}

        if mode == TradingMode.LIVE:
            p = self.portfolio.open_position
            order = {
                "symbol": p.symbol,
                "qty": p.qty,
                "type": 2,
                "side": -1 if p.side == "BUY" else 1,
                "productType": "INTRADAY",
            }
            self.fyers.place_order(order)

        pnl = self.portfolio.close_trade(ltp, reason)
        self.logger.info(
            "mode=%s action=EXIT timestamp=%s reason=%s pnl=%s",
            mode.value,
            datetime.now().isoformat(),
            reason,
            pnl,
        )
        return {"status": "closed", "mode": mode.value, "pnl": pnl}
