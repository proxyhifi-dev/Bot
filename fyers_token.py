from fyers_apiv3 import fyersModel
import os
from dotenv import load_dotenv

load_dotenv()

client_id = os.getenv("FYERS_CLIENT_ID")
secret_key = os.getenv("FYERS_SECRET_KEY")
redirect_uri = os.getenv("FYERS_REDIRECT_URI")

auth_code = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhcHBfaWQiOiJCOEMwRVBBM0Q5IiwidXVpZCI6ImY3Yjg5YmY2OTk5ZTQ0NmNhYmE4OGI4MGJlODVhMjA2IiwiaXBBZGRyIjoiIiwibm9uY2UiOiIiLCJzY29wZSI6IiIsImRpc3BsYXlfbmFtZSI6IlhCMDM4NzkiLCJvbXMiOiJLMSIsImhzbV9rZXkiOiIxMTlkOGU3YWViZDkxNzM0Y2ZkMTQxZGE5YmRlNjY0M2VmOWMyOTdjNjZkZTdhYjYwNzQ4M2NlOCIsImlzRGRwaUVuYWJsZWQiOiJZIiwiaXNNdGZFbmFibGVkIjoiWSIsImF1ZCI6IltcImQ6MVwiLFwiZDoyXCIsXCJ4OjBcIixcIng6MVwiLFwieDoyXCJdIiwiZXhwIjoxNzcxMTg5ODAyLCJpYXQiOjE3NzExNTk4MDIsImlzcyI6ImFwaS5sb2dpbi5meWVycy5pbiIsIm5iZiI6MTc3MTE1OTgwMiwic3ViIjoiYXV0aF9jb2RlIn0.jlst-0PVOmvx2ZmRvVsSuCXDfgrJAUvjGviAgRVUvFw"   # 👈 ఇక్కడ paste చేయి

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
