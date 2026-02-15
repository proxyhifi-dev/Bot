from fyers_apiv3 import fyersModel
import os
from dotenv import load_dotenv

load_dotenv()

client_id = os.getenv("FYERS_CLIENT_ID")
redirect_uri = os.getenv("FYERS_REDIRECT_URI")

session = fyersModel.SessionModel(
    client_id=client_id,
    redirect_uri=redirect_uri,
    response_type="code",
    grant_type="authorization_code"
)

print("Login URL:")
print(session.generate_authcode())
