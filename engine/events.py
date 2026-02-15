# engine/events.py

class Event:
    pass


class MarketEvent(Event):
    def __init__(self, symbol, price):
        self.symbol = symbol
        self.price = price


class SignalEvent(Event):
    def __init__(self, symbol, action, price):
        self.symbol = symbol
        self.action = action
        self.price = price


class OrderEvent(Event):
    def __init__(self, symbol, action, qty, price):
        self.symbol = symbol
        self.action = action
        self.qty = qty
        self.price = price
