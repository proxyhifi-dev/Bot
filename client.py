import os
from fyers_apiv3 import fyersModel
from dotenv import load_dotenv

load_dotenv()

client_id = os.getenv("FYERS_CLIENT_ID")
access_token = os.getenv("FYERS_ACCESS_TOKEN")

fyers = fyersModel.FyersModel(
    client_id=client_id,
    token=access_token,
    log_path="logs"
)

print("✅ FYERS client ready")
