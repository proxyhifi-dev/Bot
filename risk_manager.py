import math
from typing import Optional

class RiskManager:
    """
    Manages risk per trade based on capital and risk percentage.
    """
    def __init__(self, capital: float = 100000, risk_per_trade: float = 0.01):
        """
        Args:
            capital (float): Total trading capital.
            risk_per_trade (float): Fraction of capital to risk per trade.
        """
        self.capital = capital
        self.risk = risk_per_trade

    def get_qty(self, entry: float, stoploss: float) -> int:
        """
        Calculate position size based on entry and stoploss.

        Args:
            entry (float): Entry price.
            stoploss (float): Stoploss price.

        Returns:
            int: Quantity to trade. Returns 0 if stoploss equals entry.
        """
        risk_amount = self.capital * self.risk
        per_share_risk = abs(entry - stoploss)
        if per_share_risk == 0:
            return 0
        return math.floor(risk_amount / per_share_risk)
