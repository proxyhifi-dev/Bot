import os
from dotenv import load_dotenv
from engine.trading_engine import TradingEngine
from engine.live_data import LiveMarketData

load_dotenv()

access_token = os.getenv("FYERS_ACCESS_TOKEN")

if not access_token:
    print("❌ No access token found in .env")
    exit()

print("\n🚀 Starting LIVE NIFTY Paper Trading Bot...\n")

engine = TradingEngine()
live_data = LiveMarketData(access_token, engine)

live_data.start()
