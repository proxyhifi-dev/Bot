import os
from fyers_apiv3 import fyersModel
from dotenv import load_dotenv, set_key

load_dotenv()

def exchange_token(auth_code):
    """Exchanges auth_code for access_token and updates .env"""
    client_id = os.getenv("FYERS_CLIENT_ID")
    secret_key = os.getenv("FYERS_SECRET_KEY")
    redirect_uri = os.getenv("FYERS_REDIRECT_URI")

    # Initialize session for exchange
    session = fyersModel.SessionModel(
        client_id=client_id,
        secret_key=secret_key,
        redirect_uri=redirect_uri,
        response_type="code",
        grant_type="authorization_code"
    )

    # Set the auth_code and generate token
    session.set_token(auth_code)
    response = session.generate_token()

    if "access_token" in response:
        token = response["access_token"]
        # Save to .env automatically
        set_key(".env", "FYERS_ACCESS_TOKEN", token)
        print("✅ Access Token generated and saved to .env")
        return token
    else:
        print(f"❌ Exchange Failed: {response}")
        return None

if __name__ == "__main__":
    # Paste your long auth_code here or use input()
    code = input("Paste your auth_code: ")
    exchange_token(code)