class RiskManager:
    def __init__(self, capital, risk_per_trade=0.01):
        self.capital = capital
        self.risk_per_trade = risk_per_trade
        self.daily_loss = 0
        self.max_daily_loss = capital * 0.03  # 3% max daily

    def calculate_position_size(self, entry_price, stop_loss):
        risk_amount = self.capital * self.risk_per_trade
        risk_per_unit = abs(entry_price - stop_loss)

        if risk_per_unit == 0:
            return 0

        qty = risk_amount / risk_per_unit
        return int(qty)

    def can_trade(self):
        return self.daily_loss < self.max_daily_loss

    def update_loss(self, loss):
        self.daily_loss += loss

