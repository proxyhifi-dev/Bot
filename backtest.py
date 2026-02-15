import random
from engine.trading_engine import TradingEngine

engine = TradingEngine()

print("📊 Running Backtest...\n")

price = 21900

for _ in range(200):
    price += random.randint(-30, 30)
    engine.on_market_data("NIFTY", price)
    engine.run()

print("\n✅ Backtest Complete")
