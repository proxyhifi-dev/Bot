from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime
import threading
from typing import Optional, List, Dict


@dataclass
class Position:
    symbol: str
    side: str
    qty: int
    entry_price: float
    stop_loss: float
    target: float
    mode: str
    entry_time: str


class Portfolio:
    def __init__(self):
        self.open_position: Optional[Position] = None
        self.realized_pnl = 0.0
        self.equity_curve: List[float] = [0.0]
        self.trades: List[Dict] = []
        self._lock = threading.Lock()

    def has_open_position(self) -> bool:
        with self._lock:
            return self.open_position is not None

    def open_trade(
        self,
        symbol: str,
        side: str,
        qty: int,
        entry_price: float,
        stop_loss: float,
        target: float,
        mode: str,
    ) -> Position:
        with self._lock:
            self.open_position = Position(
                symbol=symbol,
                side=side,
                qty=qty,
                entry_price=entry_price,
                stop_loss=stop_loss,
                target=target,
                mode=mode,
                entry_time=datetime.now().isoformat(),
            )
            return self.open_position

    def get_open_position(self) -> Optional[Position]:
        with self._lock:
            return self.open_position

    def close_trade(self, exit_price: float, reason: str) -> float:
        with self._lock:
            if not self.open_position:
                return 0.0

            p = self.open_position
            direction = 1 if p.side.upper() == "BUY" else -1
            pnl = (exit_price - p.entry_price) * p.qty * direction
            self.realized_pnl += pnl
            self.equity_curve.append(self.realized_pnl)

            self.trades.append(
                {
                    "symbol": p.symbol,
                    "side": p.side,
                    "qty": p.qty,
                    "entry": p.entry_price,
                    "exit": exit_price,
                    "pnl": pnl,
                    "mode": p.mode,
                    "entry_time": p.entry_time,
                    "exit_time": datetime.now().isoformat(),
                    "reason": reason,
                }
            )
            self.open_position = None
            return pnl

    def mark_to_market(self, ltp: float) -> float:
        with self._lock:
            if not self.open_position:
                return self.realized_pnl
            p = self.open_position
            direction = 1 if p.side.upper() == "BUY" else -1
            unrealized = (ltp - p.entry_price) * p.qty * direction
            return self.realized_pnl + unrealized

    def trades_snapshot(self) -> List[Dict]:
        with self._lock:
            return list(self.trades)

    def stats(self) -> Dict:
        with self._lock:
            wins = sum(1 for t in self.trades if t["pnl"] > 0)
            total = len(self.trades)
            peak = float("-inf")
            max_dd = 0.0
            for e in self.equity_curve:
                peak = max(peak, e)
                max_dd = max(max_dd, peak - e)
            return {
                "realized_pnl": self.realized_pnl,
                "total_trades": total,
                "win_rate": (wins / total * 100) if total else 0.0,
                "max_drawdown": max_dd,
                "open_position": asdict(self.open_position) if self.open_position else None,
            }
