import pandas as pd
import ta

class SupertrendStrategy:

    def generate_signal(self, candles):
        df = pd.DataFrame(
            candles,
            columns=["timestamp", "open", "high", "low", "close", "volume"]
        )

        df["supertrend"] = ta.trend.STCIndicator(
            close=df["close"]
        ).stc()

        if df["close"].iloc[-1] > df["close"].iloc[-2]:
            return "BUY"
        elif df["close"].iloc[-1] < df["close"].iloc[-2]:
            return "SELL"

        return None
