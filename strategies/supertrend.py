import pandas_ta as ta

class SupertrendStrategy:
    """
    Supertrend strategy using pandas_ta. Returns 'BUY', 'SELL', or 'WAIT' based on trend change.
    """
    def __init__(self, length=10, multiplier=3):
        self.length = length
        self.multiplier = multiplier

    def analyze(self, df):
        # Ensure DataFrame has enough rows
        if len(df) < 2:
            return "WAIT"

        st = ta.supertrend(
            df["high"],
            df["low"],
            df["close"],
            length=self.length,
            multiplier=self.multiplier
        )
        df = df.join(st)

        # Find the trend column robustly
        trend_cols = [c for c in df.columns if c.upper().startswith("SUPERTD") or "SUPERTD" in c.upper()]
        if not trend_cols:
            raise ValueError("Supertrend column not found in DataFrame after applying ta.supertrend.")
        trend_col = trend_cols[0]

        # Check for trend change
        if df[trend_col].iloc[-1] == 1 and df[trend_col].iloc[-2] == -1:
            return "BUY"
        if df[trend_col].iloc[-1] == -1 and df[trend_col].iloc[-2] == 1:
            return "SELL"
        return "WAIT"
