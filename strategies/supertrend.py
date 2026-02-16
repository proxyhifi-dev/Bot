from __future__ import annotations

from typing import Dict, List, Optional


def _atr(candles: List[List[float]], period: int) -> List[float]:
    trs = []
    for i, c in enumerate(candles):
        high, low, close = c[2], c[3], c[4]
        prev_close = candles[i - 1][4] if i > 0 else close
        tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
        trs.append(tr)

    atr = []
    for i in range(len(trs)):
        window = trs[max(0, i - period + 1): i + 1]
        atr.append(sum(window) / len(window))
    return atr


class SupertrendStrategy:
    def __init__(self, period: int = 10, multiplier: float = 3.0):
        self.period = period
        self.multiplier = multiplier

    def generate_signal(self, candles: List[List[float]]) -> Optional[str]:
        if len(candles) < self.period + 2:
            return None

        atr_vals = _atr(candles, self.period)
        i = len(candles) - 1
        prev_i = i - 1

        high, low, close = candles[i][2], candles[i][3], candles[i][4]
        ph, pl, pclose = candles[prev_i][2], candles[prev_i][3], candles[prev_i][4]

        hl2 = (high + low) / 2
        phl2 = (ph + pl) / 2

        upper = hl2 + self.multiplier * atr_vals[i]
        lower = hl2 - self.multiplier * atr_vals[i]
        prev_upper = phl2 + self.multiplier * atr_vals[prev_i]
        prev_lower = phl2 - self.multiplier * atr_vals[prev_i]

        if pclose <= prev_upper and close > upper:
            return "BUY"
        if pclose >= prev_lower and close < lower:
            return "SELL"
        return None

    def build_trade_signal(self, symbol: str, side: str, ltp: float, qty: int) -> Dict:
        sl_offset = 50.0
        target_offset = 100.0
        stop_loss = ltp - sl_offset if side == "BUY" else ltp + sl_offset
        target = ltp + target_offset if side == "BUY" else ltp - target_offset
        return {
            "symbol": symbol,
            "side": side,
            "qty": qty,
            "stop_loss": stop_loss,
            "target": target,
        }
