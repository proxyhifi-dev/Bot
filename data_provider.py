import os
from fyers_apiv3 import fyersModel
from dotenv import load_dotenv

def get_fyers_client():
    load_dotenv() # Reload to get the fresh token
    return fyersModel.FyersModel(
        client_id=os.getenv("FYERS_CLIENT_ID"),
        token=os.getenv("FYERS_ACCESS_TOKEN"),
        log_path="logs"
    )

def get_option_chain(symbol):
    fyers = get_fyers_client()
    data = {"symbol": symbol, "strikecount": 10, "timestamp": ""}
    response = fyers.optionchain(data)
    
    if response["s"] != "ok":
        raise Exception(f"API Error: {response}")
    return response["data"]