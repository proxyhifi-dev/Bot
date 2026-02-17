from __future__ import annotations

import time
from typing import List

from execution.fyers_adapter import FyersAdapter


class DataProvider:
    def __init__(self, fyers_adapter: FyersAdapter):
        self.fyers = fyers_adapter

    def get_latest_data(self, symbol: str, timeframe: str = "5") -> List[List[float]]:
        """
        Fetch recent candles for indicator calculation.
        Returns list of candles in FYERS format:
        [epoch, open, high, low, close, volume]
        """
        to_date = int(time.time())
        from_date = to_date - (5 * 24 * 60 * 60)

        candles = self.fyers.get_history(
            symbol=symbol,
            resolution=timeframe,
            range_from=str(from_date),
            range_to=str(to_date),
        )

        if not candles:
            raise ValueError(f"No data received for {symbol}")

        return candles
