class TradingEngine:
    def __init__(self, strategy, execution, risk, portfolio):
        self.strategy = strategy
        self.execution = execution
        self.risk = risk
        self.portfolio = portfolio

    async def on_market_data(self, data):
        signal = self.strategy.generate_signal(data)
        if signal and self.risk.validate(signal, self.portfolio):
            await self.execution.execute(signal)