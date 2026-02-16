from __future__ import annotations

from dataclasses import dataclass
from typing import List

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
    def __init__(self, symbol: str = "NSE:NIFTY50-INDEX"):
        self.symbol = symbol
        self.fyers = FyersAdapter()
        self.strategy = SupertrendStrategy(10, 3)

    def run(self) -> BacktestResult:
        candles = self.fyers.get_history(self.symbol)
        if len(candles) < 50:
            raise RuntimeError("Insufficient historical data from Fyers")

        in_pos = False
        entry = 0.0
        pnl_list: List[float] = []
        equity = 0.0
        peak = 0.0
        max_dd = 0.0

        for i in range(20, len(candles)):
            chunk = candles[: i + 1]
            sig = self.strategy.generate_signal(chunk)
            ltp = chunk[-1][4]
            if not in_pos and sig == "BUY":
                in_pos = True
                entry = ltp
            elif in_pos and sig == "SELL":
                pnl = ltp - entry
                pnl_list.append(pnl)
                equity += pnl
                peak = max(peak, equity)
                max_dd = max(max_dd, peak - equity)
                in_pos = False

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
    r = SupertrendBacktester().run()
    print("Backtest complete")
    print(f"Total Trades: {r.total_trades}")
    print(f"Win Rate: {r.win_rate:.2f}%")
    print(f"Net PnL: {r.net_pnl:.2f}")
    print(f"Max Drawdown: {r.max_drawdown:.2f}")
    print(f"Profit Factor: {r.profit_factor:.2f}")
