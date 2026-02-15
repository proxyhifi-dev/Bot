class Portfolio:
    def __init__(self):
        self.positions = {}
        self.realized_pnl = 0

    def add_position(self, symbol, qty, entry_price):
        self.positions[symbol] = {
            "qty": qty,
            "entry_price": entry_price
        }

    def close_position(self, symbol, exit_price):
        if symbol not in self.positions:
            return 0

        position = self.positions[symbol]
        pnl = (exit_price - position["entry_price"]) * position["qty"]

        self.realized_pnl += pnl
        del self.positions[symbol]

        return pnl
