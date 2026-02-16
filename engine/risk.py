from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time


@dataclass
class RiskSnapshot:
    trades_today: int
    losses_today: int
    blocked: bool
    reason: str


class RiskManager:
    def __init__(
        self,
        capital: float,
        risk_per_trade: float = 0.01,
        max_trades_per_day: int = 3,
        max_losses_per_day: int = 2,
        no_new_trades_after: time = time(14, 45),
        force_square_off: time = time(15, 15),
    ):
        self.capital = capital
        self.risk_per_trade = risk_per_trade
        self.max_trades_per_day = max_trades_per_day
        self.max_losses_per_day = max_losses_per_day
        self.no_new_trades_after = no_new_trades_after
        self.force_square_off = force_square_off

        self._trades_today = 0
        self._losses_today = 0
        self._last_reset_day = datetime.now().date()

    def _roll_day(self) -> None:
        today = datetime.now().date()
        if today != self._last_reset_day:
            self._trades_today = 0
            self._losses_today = 0
            self._last_reset_day = today

    def calculate_position_size(self, entry_price: float, stop_loss: float) -> int:
        risk_per_unit = abs(entry_price - stop_loss)
        if risk_per_unit <= 0:
            return 0
        risk_amount = self.capital * self.risk_per_trade
        return max(int(risk_amount / risk_per_unit), 0)

    def can_open_new_trade(self, now: datetime) -> RiskSnapshot:
        self._roll_day()
        if now.time() > self.no_new_trades_after:
            return RiskSnapshot(self._trades_today, self._losses_today, True, "No new trade after 2:45 PM")
        if self._trades_today >= self.max_trades_per_day:
            return RiskSnapshot(self._trades_today, self._losses_today, True, "Max trades/day reached")
        if self._losses_today >= self.max_losses_per_day:
            return RiskSnapshot(self._trades_today, self._losses_today, True, "Stopped after 2 losses")
        return RiskSnapshot(self._trades_today, self._losses_today, False, "")

    def register_trade(self, pnl: float) -> None:
        self._roll_day()
        self._trades_today += 1
        if pnl < 0:
            self._losses_today += 1

    def should_force_square_off(self, now: datetime) -> bool:
        return now.time() >= self.force_square_off

    @property
    def trades_today(self) -> int:
        self._roll_day()
        return self._trades_today

    @property
    def losses_today(self) -> int:
        self._roll_day()
        return self._losses_today
