import os
import pyotp
from dotenv import load_dotenv

load_dotenv()

client_id = os.getenv("FYERS_CLIENT_ID")
totp_key = os.getenv("FYERS_TOTP_KEY")

print("DEBUG CLIENT_ID :", client_id)
print("DEBUG TOTP_KEY  :", totp_key)

if not totp_key:
    raise Exception("❌ FYERS_TOTP_KEY is missing in .env")

try:
    totp = pyotp.TOTP(totp_key)
    otp = totp.now()
    print("✅ Current TOTP:", otp)
except Exception as e:
    raise Exception(f"❌ Invalid TOTP Secret Key: {e}")

print(
    "1. Login here:",
    f"https://api-t1.fyers.in/api/v3/generate-authcode"
    f"?client_id={client_id}"
    f"&redirect_uri=http://localhost:4200/auth/fyers/callback"
    f"&response_type=code&state=state123"
)
