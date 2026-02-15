class Portfolio:
    def __init__(self):
        self.positions = {}
        self.pnl = 0

    def update_position(self, symbol, qty, price):
        self.positions[symbol] = {"qty": qty, "price": price}