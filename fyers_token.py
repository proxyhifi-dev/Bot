from fyers_apiv3 import fyersModel
import os
from dotenv import load_dotenv, set_key

load_dotenv()

def exchange_token(auth_code):
    client_id = os.getenv("FYERS_CLIENT_ID")
    secret_key = os.getenv("FYERS_SECRET_KEY")
    redirect_uri = os.getenv("FYERS_REDIRECT_URI")

    session = fyersModel.SessionModel(
        client_id=client_id,
        secret_key=secret_key,
        redirect_uri=redirect_uri,
        response_type="code",
        grant_type="authorization_code"
    )

    session.set_token(auth_code)
    response = session.generate_token()

    print("ACCESS TOKEN RESPONSE:")
    print(response)

    if response.get("access_token"):
        token = response["access_token"]
        set_key(".env", "FYERS_ACCESS_TOKEN", token)
        print("✅ Access Token saved to .env")
        return token
    else:
        print("❌ Token exchange failed")
        return None


if __name__ == "__main__":
    auth_code = input("Paste fresh auth_code here: ")
    exchange_token(auth_code)
