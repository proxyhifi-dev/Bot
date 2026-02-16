from __future__ import annotations

from datetime import datetime, timedelta
import json
import logging
import threading
import time
import uuid
from typing import Any, Dict, Optional

from engine.execution import TradeExecutor
from engine.live_data import LiveMarketData
from engine.mode import ModeManager, TradingMode
from engine.portfolio import Portfolio
from engine.risk import RiskManager
from execution.fyers_adapter import FyersAdapter
from strategies.supertrend import SupertrendStrategy


class TradingEngine:
    APPROVAL_TIMEOUT_SECONDS = 60

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

        self.pending_signal: Optional[Dict[str, Any]] = None
        self.pending_expiry: Optional[datetime] = None
        self.pending_correlation_id: Optional[str] = None
        self.last_signal: Optional[str] = None

        self._state_lock = threading.Lock()
        self._stop_event = threading.Event()
        self._running = False
        self._engine_thread: Optional[threading.Thread] = None
        self._approval_timeout_thread = threading.Thread(
            target=self._approval_timeout_loop,
            name="approval-timeout-engine",
            daemon=True,
        )
        self._approval_timeout_thread.start()

    def _approval_timeout_loop(self) -> None:
        while not self._stop_event.is_set():
            timed_out_signal: Optional[Dict] = None
            timed_out_corr_id: Optional[str] = None
            now = datetime.now()
            with self._state_lock:
                if self.pending_signal and self.pending_expiry and now > self.pending_expiry:
                    timed_out_signal = self.pending_signal
                    timed_out_corr_id = self.pending_correlation_id
                    self.pending_signal = None
                    self.pending_expiry = None
                    self.pending_correlation_id = None

            if timed_out_signal:
                self.logger.info(
                    "approval=TIMEOUT timestamp=%s correlation_id=%s signal=%s",
                    now.isoformat(),
                    timed_out_corr_id,
                    timed_out_signal,
                )
            time.sleep(1)

    def stop(self) -> None:
        self._stop_event.set()
        if self._engine_thread and self._engine_thread.is_alive():
            self._engine_thread.join(timeout=3)
        if self._approval_timeout_thread.is_alive():
            self._approval_timeout_thread.join(timeout=2)
        self._running = False

    def start(self) -> None:
        if self._running:
            return
        self._stop_event.clear()
        self._running = True
        self._engine_thread = threading.Thread(target=self._engine_loop, name="trading-engine-loop", daemon=True)
        self._engine_thread.start()

    def _engine_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                result = self.evaluate_market()
                if result.get("event") in {"risk_block", "no_candles"}:
                    time.sleep(2)
                else:
                    time.sleep(1)
            except Exception as exc:  # pragma: no cover - defensive safety loop
                self.logger.exception("engine_loop_error error=%s", exc)
                time.sleep(5)

    def emergency_stop(self) -> Dict[str, Any]:
        self.stop()
        self._log_event("emergency_stop", details={"stopped": True})
        return {"status": "stopped"}

    def bootstrap_live_positions(self) -> None:
        if self.mode_manager.mode != TradingMode.LIVE:
            return
        positions = self.fyers.get_positions()
        if positions:
            self._log_event("live_positions_detected", details={"positions": positions})

    def evaluate_market(self) -> Dict[str, Any]:
        candles = self.data.latest_5m_candles()
        if not candles:
            return {"event": "no_candles"}
        ltp = float(candles[-1][4])
        now = datetime.now()

        if self.risk.should_force_square_off(now) and self.portfolio.has_open_position():
            result = self.executor.exit_trade(ltp, "Force square-off 3:15 PM")
            self.risk.register_trade(result.get("pnl", 0.0))
            self._log_event("force_square_off", details={"result": result})
            return {"event": "force_square_off", "result": result}

        open_position = self.portfolio.get_open_position()
        if open_position:
            p = open_position
            if (p.side == "BUY" and (ltp <= p.stop_loss or ltp >= p.target)) or (
                p.side == "SELL" and (ltp >= p.stop_loss or ltp <= p.target)
            ):
                reason = "SL hit" if (ltp <= p.stop_loss if p.side == "BUY" else ltp >= p.stop_loss) else "Target hit"
                result = self.executor.exit_trade(ltp, reason)
                self.risk.register_trade(result.get("pnl", 0.0))
                self._log_event("position_exit", details={"reason": reason, "result": result})
                return {"event": "position_exit", "result": result}
            return {"event": "position_holding", "ltp": ltp}

        risk_snapshot = self.risk.can_open_new_trade(now)
        if risk_snapshot.blocked:
            return {"event": "risk_block", "reason": risk_snapshot.reason}

        signal = self.strategy.generate_signal(candles)
        with self._state_lock:
            self.last_signal = signal
        if signal in {"BUY", "SELL"}:
            qty = self.risk.calculate_position_size(ltp, ltp - 50 if signal == "BUY" else ltp + 50)
            if qty <= 0:
                return {"event": "invalid_qty"}
            built_signal = self.strategy.build_trade_signal(self.symbol, signal, ltp, qty)
            corr_id = str(uuid.uuid4())
            with self._state_lock:
                self.pending_signal = built_signal
                self.pending_expiry = now + timedelta(seconds=self.APPROVAL_TIMEOUT_SECONDS)
                self.pending_correlation_id = corr_id
                pending_expiry = self.pending_expiry
            self.logger.info(
                "mode=%s signal=%s price=%s qty=%s pending_approval_until=%s correlation_id=%s",
                self.mode_manager.mode.value,
                signal,
                ltp,
                qty,
                pending_expiry.isoformat(),
                corr_id,
            )
            return {"event": "signal_generated", "signal": built_signal, "correlation_id": corr_id}

        return {"event": "no_signal"}

    def approve_pending_signal(self) -> Dict:
        with self._state_lock:
            pending_signal = self.pending_signal
            pending_expiry = self.pending_expiry
            corr_id = self.pending_correlation_id

        if not pending_signal:
            return {"status": "no_pending_signal"}

        if pending_expiry and datetime.now() > pending_expiry:
            with self._state_lock:
                self.pending_signal = None
                self.pending_expiry = None
                self.pending_correlation_id = None
            self.logger.info(
                "approval=EXPIRED timestamp=%s correlation_id=%s",
                datetime.now().isoformat(),
                corr_id,
            )
            return {"status": "expired", "correlation_id": corr_id}

        ltp = self.data.latest_ltp()
        result = self.executor.enter_trade(pending_signal, ltp)
        self.logger.info(
            "mode=%s approval=APPROVED signal=%s correlation_id=%s",
            self.mode_manager.mode.value,
            pending_signal,
            corr_id,
        )
        with self._state_lock:
            self.pending_signal = None
            self.pending_expiry = None
            self.pending_correlation_id = None
        result["correlation_id"] = corr_id
        return result

    def reject_pending_signal(self) -> Dict:
        with self._state_lock:
            pending_signal = self.pending_signal
            corr_id = self.pending_correlation_id
            if not pending_signal:
                return {"status": "no_pending_signal"}
            self.pending_signal = None
            self.pending_expiry = None
            self.pending_correlation_id = None

        self.logger.info(
            "mode=%s approval=REJECTED signal=%s correlation_id=%s",
            self.mode_manager.mode.value,
            pending_signal,
            corr_id,
        )
        return {"status": "rejected", "correlation_id": corr_id}

    def switch_mode(self, target_mode: TradingMode, confirm_live: bool) -> Dict[str, Any]:
        event = self.mode_manager.switch_mode(
            target_mode=target_mode,
            has_open_position=self.portfolio.has_open_position(),
            confirm_live=confirm_live,
            auth_validator=self.fyers.validate_token,
        )
        self._log_event("mode_switched", details={"from": event.from_mode.value, "to": event.to_mode.value})
        return {"from": event.from_mode.value, "to": event.to_mode.value, "reason": event.reason}

    def approval_countdown(self) -> int:
        with self._state_lock:
            pending_expiry = self.pending_expiry
        if not pending_expiry:
            return 0
        return max(int((pending_expiry - datetime.now()).total_seconds()), 0)

    def status(self) -> Dict[str, Any]:
        stats = self.portfolio.stats()
        with self._state_lock:
            pending_signal = self.pending_signal
            last_signal = self.last_signal
            corr_id = self.pending_correlation_id
        return {
            "mode": self.mode_manager.mode.value,
            "bot_status": "RUNNING" if self._running and not self._stop_event.is_set() else "STOPPED",
            "position": stats["open_position"],
            "today_pnl": stats["realized_pnl"],
            "pending_signal": pending_signal,
            "pending_correlation_id": corr_id,
            "approval_countdown": self.approval_countdown(),
            "win_rate": stats["win_rate"],
            "drawdown": stats["max_drawdown"],
            "trades_today": self.risk.trades_today,
            "losses_today": self.risk.losses_today,
            "last_signal": last_signal,
        }

    def _log_event(self, event: str, details: Dict[str, Any]) -> None:
        payload = {
            "timestamp": datetime.now().isoformat(),
            "event": event,
            "mode": self.mode_manager.mode.value,
            "trade_id": self.pending_correlation_id,
            "details": details,
        }
        self.logger.info(json.dumps(payload))
