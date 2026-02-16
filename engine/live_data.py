from __future__ import annotations

from datetime import datetime, timedelta
from typing import List

from execution.fyers_adapter import FyersAdapter


class LiveMarketData:
    def __init__(self, fyers: FyersAdapter, symbol: str = "NSE:NIFTY50-INDEX"):
        self.fyers = fyers
        self.symbol = symbol

    def latest_ltp(self) -> float:
        return self.fyers.get_ltp(self.symbol)

    def latest_5m_candles(self, lookback: int = 150) -> List[List[float]]:
        end = int(datetime.now().timestamp())
        start = int((datetime.now() - timedelta(days=5)).timestamp())
        candles = self.fyers.get_history(
            symbol=self.symbol,
            resolution="5",
            range_from=str(start),
            range_to=str(end),
        )
        return candles[-lookback:]
