from fyers_apiv3 import fyersModel
import os
from dotenv import load_dotenv

load_dotenv()

fyers = fyersModel.FyersModel(
    client_id=os.getenv("FYERS_CLIENT_ID"),
    token=os.getenv("FYERS_ACCESS_TOKEN"),
    log_path="logs"
)

def get_option_chain(symbol):
    data = {
        "symbol": symbol,
        "strikecount": 10,
        "timestamp": ""
    }

    response = fyers.optionchain(data)

    if response["s"] != "ok":
        raise Exception(response)

    return response["data"]
