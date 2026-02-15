import pandas as pd
import pandas_ta as ta
from typing import Optional

class SupertrendStrategy:
    """
    Supertrend strategy using pandas_ta. Returns 'BUY', 'SELL', or 'WAIT' based on trend change.
    """
    def __init__(self, length: int = 10, multiplier: float = 3):
        """
        Args:
            length (int): Supertrend period length.
            multiplier (float): Supertrend multiplier.
        """
        self.length = length
        self.multiplier = multiplier

    def analyze(self, df: pd.DataFrame) -> str:
        """
        Analyze the DataFrame and return a trading signal based on Supertrend.

        Args:
            df (pd.DataFrame): DataFrame with 'high', 'low', 'close' columns.

        Returns:
            str: 'BUY', 'SELL', or 'WAIT'
        """
        if len(df) < 2:
            return "WAIT"

        st = ta.supertrend(df['high'], df['low'], df['close'], length=self.length, multiplier=self.multiplier)
        df = df.join(st)

        # Robustly find the Supertrend direction column
        trend_cols = [c for c in df.columns if c.upper().startswith("SUPERTD") or "SUPERTD" in c.upper()]
        if not trend_cols:
            raise ValueError("Supertrend column not found in DataFrame after applying ta.supertrend.")
        col = trend_cols[0]

        curr, prev = df[col].iloc[-1], df[col].iloc[-2]

        if curr == 1 and prev == -1:
            return "BUY"
        if curr == -1 and prev == 1:
            return "SELL"
        return "WAIT"