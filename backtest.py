from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional

from execution.fyers_adapter import FyersAdapter
from strategies.supertrend import SupertrendStrategy


@dataclass
class BacktestResult:
    total_trades: int
    win_rate: float
    net_pnl: float
    max_drawdown: float
    profit_factor: float


class SupertrendBacktester:
    def __init__(self, symbol: str = "NSE:NIFTY50-INDEX", resolution: str = "5"):
        self.symbol = symbol
        self.resolution = resolution
        self.fyers = FyersAdapter()
        self.strategy = SupertrendStrategy(10, 3)

    def _fetch_data(self, days: int = 60) -> List[List[float]]:
        self.fyers.ensure_authenticated(interactive=True)
        end = int(datetime.now().timestamp())
        start = int((datetime.now() - timedelta(days=days)).timestamp())
        candles = self.fyers.get_history(
            symbol=self.symbol,
            resolution=self.resolution,
            range_from=str(start),
            range_to=str(end),
        )
        if len(candles) < 100:
            raise RuntimeError("Insufficient historical data from Fyers for backtest")
        return candles

    def run(self) -> BacktestResult:
        candles = self._fetch_data()

        position: Optional[str] = None
        entry_price = 0.0
        pnl_list: List[float] = []
        equity = 0.0
        peak = 0.0
        max_dd = 0.0

        for i in range(20, len(candles)):
            chunk = candles[: i + 1]
            signal = self.strategy.generate_signal(chunk)
            ltp = float(chunk[-1][4])

            if position is None and signal in {"BUY", "SELL"}:
                position = signal
                entry_price = ltp
                continue

            if position == "BUY" and signal == "SELL":
                pnl = ltp - entry_price
                pnl_list.append(pnl)
                position = None
            elif position == "SELL" and signal == "BUY":
                pnl = entry_price - ltp
                pnl_list.append(pnl)
                position = None
            else:
                continue

            equity += pnl_list[-1]
            peak = max(peak, equity)
            max_dd = max(max_dd, peak - equity)

        wins = [p for p in pnl_list if p > 0]
        losses = [abs(p) for p in pnl_list if p < 0]
        total = len(pnl_list)
        pf = (sum(wins) / sum(losses)) if losses else float("inf")

        return BacktestResult(
            total_trades=total,
            win_rate=(len(wins) / total * 100) if total else 0.0,
            net_pnl=sum(pnl_list),
            max_drawdown=max_dd,
            profit_factor=pf,
        )


if __name__ == "__main__":
    result = SupertrendBacktester().run()
    print("Backtest complete")
    print(f"Total Trades: {result.total_trades}")
    print(f"Win Rate: {result.win_rate:.2f}%")
    print(f"Net PnL: {result.net_pnl:.2f}")
    print(f"Max Drawdown: {result.max_drawdown:.2f}")
    print(f"Profit Factor: {result.profit_factor:.2f}")
