import os
import pyotp
from fyers_apiv3 import fyersModel
from dotenv import load_dotenv, set_key

load_dotenv()

def get_session():
    return fyersModel.SessionModel(
        client_id=os.getenv("FYERS_APP_ID"),
        secret_key=os.getenv("FYERS_SECRET_ID"),
        redirect_uri=os.getenv("FYERS_REDIRECT_URI"),
        response_type='code', grant_type='authorization_code'
    )

def generate_access_token(auth_code):
    """Exchanges auth_code for access_token and updates .env"""
    session = get_session()
    session.set_token(auth_code)
    response = session.generate_token()
    
    if "access_token" in response:
        token = response["access_token"]
        # Save to .env so main.py can see it
        set_key(".env", "FYERS_ACCESS_TOKEN", token)
        print("✅ Access Token generated and saved to .env")
        return token
    else:
        print(f"❌ Error: {response}")
        return None

if __name__ == "__main__":
    session = get_session()
    print(f"1. Login here: {session.generate_authcode()}")
    print(f"2. Your current TOTP: {pyotp.TOTP(os.getenv('FYERS_TOTP_KEY')).now()}")
    
    code = input("3. Paste the 'auth_code' from the redirected URL: ")
    generate_access_token(code)