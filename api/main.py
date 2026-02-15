from fastapi import FastAPI
"""
Production-ready import fix:
To run this API reliably, always start FastAPI from the project root:
    uvicorn api.main:app --reload
This ensures the parent directory is in PYTHONPATH and imports work.
"""
import sys
import os
parent = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent not in sys.path:
    sys.path.insert(0, parent)
from database import save_trade

app = FastAPI()

@app.get("/")
def root():
    return {"status": "Bot API Running"}

@app.get("/trade_status")
def trade_status():
    # Dummy response for now
    return {"status": "No trades running"}

@app.post("/manual_trade")
def manual_trade(symbol: str, action: str, qty: int, price: float):
    # Save manual trade to database
    save_trade(symbol, action, price, qty, "manual")
    return {"message": f"Manual trade {action} {symbol} {qty} @ {price} saved."}
