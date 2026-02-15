class RollingRSI:
    def __init__(self, period=14):
        self.period = period
        self.prev_close = None
        self.avg_gain = 0
        self.avg_loss = 0
        self.counter = 0

    def update(self, close):
        if self.prev_close is None:
            self.prev_close = close
            return None

        change = close - self.prev_close
        gain = max(change, 0)
        loss = max(-change, 0)

        if self.counter < self.period:
            self.avg_gain += gain
            self.avg_loss += loss
            self.counter += 1
            if self.counter == self.period:
                self.avg_gain /= self.period
                self.avg_loss /= self.period
        else:
            # Wilder's Smoothing Logic
            self.avg_gain = ((self.avg_gain * (self.period - 1)) + gain) / self.period
            self.avg_loss = ((self.avg_loss * (self.period - 1)) + loss) / self.period

        self.prev_close = close
        return self.get_value()

    def get_value(self):
        if self.counter < self.period: return None
        if self.avg_loss == 0: return 100
        rs = self.avg_gain / self.avg_loss
        return 100 - (100 / (1 + rs))

class RollingATR:
    def __init__(self, period=14):
        self.period = period
        self.prev_close = None
        self.atr = 0
        self.counter = 0

    def update(self, high, low, close):
        if self.prev_close is None:
            self.prev_close = close
            return None

        tr = max(high - low, abs(high - self.prev_close), abs(low - self.prev_close))

        if self.counter < self.period:
            self.atr += tr
            self.counter += 1
            if self.counter == self.period:
                self.atr /= self.period
        else:
            self.atr = ((self.atr * (self.period - 1)) + tr) / self.period

        self.prev_close = close
        return self.atr