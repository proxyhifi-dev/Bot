from __future__ import annotations

from datetime import datetime, timedelta
import logging
from typing import Dict, Optional

from engine.execution import TradeExecutor
from engine.live_data import LiveMarketData
from engine.mode import ModeManager, TradingMode
from engine.portfolio import Portfolio
from engine.risk import RiskManager
from execution.fyers_adapter import FyersAdapter
from strategies.supertrend import SupertrendStrategy


class TradingEngine:
    def __init__(self, symbol: str = "NSE:NIFTY50-INDEX", capital: float = 100000.0):
        self.logger = logging.getLogger("trading_engine")
        self.symbol = symbol

        self.mode_manager = ModeManager(TradingMode.PAPER)
        self.fyers = FyersAdapter()
        self.data = LiveMarketData(self.fyers, symbol=symbol)
        self.portfolio = Portfolio()
        self.risk = RiskManager(capital=capital)
        self.strategy = SupertrendStrategy(period=10, multiplier=3)
        self.executor = TradeExecutor(self.mode_manager, self.portfolio, self.fyers)

        self.pending_signal: Optional[Dict] = None
        self.pending_expiry: Optional[datetime] = None
        self.last_signal: Optional[str] = None

    def bootstrap_live_positions(self) -> None:
        if self.mode_manager.mode != TradingMode.LIVE:
            return
        positions = self.fyers.get_positions()
        if positions:
            self.logger.warning("Broker has open positions at startup: %s", positions)

    def evaluate_market(self) -> Dict:
        candles = self.data.latest_5m_candles()
        ltp = float(candles[-1][4])
        now = datetime.now()

        if self.risk.should_force_square_off(now) and self.portfolio.has_open_position():
            result = self.executor.exit_trade(ltp, "Force square-off 3:15 PM")
            self.risk.register_trade(result.get("pnl", 0.0))
            return {"event": "force_square_off", "result": result}

        if self.portfolio.has_open_position():
            p = self.portfolio.open_position
            if (p.side == "BUY" and (ltp <= p.stop_loss or ltp >= p.target)) or (
                p.side == "SELL" and (ltp >= p.stop_loss or ltp <= p.target)
            ):
                reason = "SL hit" if (ltp <= p.stop_loss if p.side == "BUY" else ltp >= p.stop_loss) else "Target hit"
                result = self.executor.exit_trade(ltp, reason)
                self.risk.register_trade(result.get("pnl", 0.0))
                return {"event": "position_exit", "result": result}
            return {"event": "position_holding", "ltp": ltp}

        risk_snapshot = self.risk.can_open_new_trade(now)
        if risk_snapshot.blocked:
            return {"event": "risk_block", "reason": risk_snapshot.reason}

        signal = self.strategy.generate_signal(candles)
        self.last_signal = signal
        if signal in {"BUY", "SELL"}:
            qty = self.risk.calculate_position_size(ltp, ltp - 50 if signal == "BUY" else ltp + 50)
            if qty <= 0:
                return {"event": "invalid_qty"}
            self.pending_signal = self.strategy.build_trade_signal(self.symbol, signal, ltp, qty)
            self.pending_expiry = now + timedelta(seconds=30)
            self.logger.info(
                "mode=%s signal=%s price=%s qty=%s pending_approval_until=%s",
                self.mode_manager.mode.value,
                signal,
                ltp,
                qty,
                self.pending_expiry.isoformat(),
            )
            return {"event": "signal_generated", "signal": self.pending_signal}

        return {"event": "no_signal"}

    def approve_pending_signal(self) -> Dict:
        if not self.pending_signal:
            return {"status": "no_pending_signal"}
        if self.pending_expiry and datetime.now() > self.pending_expiry:
            self.pending_signal = None
            self.pending_expiry = None
            return {"status": "expired"}

        ltp = self.data.latest_ltp()
        result = self.executor.enter_trade(self.pending_signal, ltp)
        self.logger.info("mode=%s approval=APPROVED signal=%s", self.mode_manager.mode.value, self.pending_signal)
        self.pending_signal = None
        self.pending_expiry = None
        return result

    def reject_pending_signal(self) -> Dict:
        if not self.pending_signal:
            return {"status": "no_pending_signal"}
        self.logger.info("mode=%s approval=REJECTED signal=%s", self.mode_manager.mode.value, self.pending_signal)
        self.pending_signal = None
        self.pending_expiry = None
        return {"status": "rejected"}

    def switch_mode(self, target_mode: TradingMode, confirm_live: bool) -> Dict:
        event = self.mode_manager.switch_mode(
            target_mode=target_mode,
            has_open_position=self.portfolio.has_open_position(),
            confirm_live=confirm_live,
            auth_validator=self.fyers.validate_token,
        )
        return {
            "from": event.from_mode.value,
            "to": event.to_mode.value,
            "reason": event.reason,
        }

    def approval_countdown(self) -> int:
        if not self.pending_expiry:
            return 0
        return max(int((self.pending_expiry - datetime.now()).total_seconds()), 0)

    def status(self) -> Dict:
        stats = self.portfolio.stats()
        return {
            "mode": self.mode_manager.mode.value,
            "bot_status": "RUNNING",
            "position": stats["open_position"],
            "today_pnl": stats["realized_pnl"],
            "pending_signal": self.pending_signal,
            "approval_countdown": self.approval_countdown(),
            "win_rate": stats["win_rate"],
            "drawdown": stats["max_drawdown"],
            "trades_today": self.risk.trades_today,
            "losses_today": self.risk.losses_today,
            "last_signal": self.last_signal,
        }
