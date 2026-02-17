# Automate Fyers Login with TOTP (Python)

This guide explains how to automate Fyers API V3 login with TOTP so you do not need to manually create an access token every day.

> ⚠️ Keep all secrets private (app secret, TOTP seed, PIN, access token). Never commit them to source control.

## Prerequisites

Before running the script:

1. Create an app in your Fyers dashboard.
2. Activate the app from the activation URL shown in the dashboard.
3. Enable TOTP-based 2FA in your Fyers account.
4. Note down:
   - `APP_ID`
   - `APP_TYPE`
   - `SECRET_KEY`
   - `FY_ID`
   - `APP_ID_TYPE`
   - `TOTP_KEY`
   - `PIN`
   - `REDIRECT_URI`

## Setup

Create a virtual environment and install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install fyers-apiv3 requests pyotp
```

## `credentials.py`

Create `credentials.py`:

```python
APP_ID = ""
APP_TYPE = ""
SECRET_KEY = ""
FY_ID = ""
APP_ID_TYPE = ""
TOTP_KEY = ""
PIN = ""
REDIRECT_URI = "https://myapi.fyers.in/"
```

## `main.py`

Use the following script to automate the login flow:

```python
import json
import requests
import pyotp
from urllib import parse
import sys
from fyers_apiv3 import fyersModel
import credentials as cr
import time as tm

APP_ID = cr.APP_ID
APP_TYPE = cr.APP_TYPE
SECRET_KEY = cr.SECRET_KEY
client_id = f"{APP_ID}-{APP_TYPE}"

FY_ID = cr.FY_ID
APP_ID_TYPE = cr.APP_ID_TYPE
TOTP_KEY = cr.TOTP_KEY
PIN = cr.PIN
REDIRECT_URI = cr.REDIRECT_URI

BASE_URL = "https://api-t2.fyers.in/vagator/v2"
BASE_URL_2 = "https://api-t1.fyers.in/api/v3"
URL_SEND_LOGIN_OTP = BASE_URL + "/send_login_otp"
URL_VERIFY_TOTP = BASE_URL + "/verify_otp"
URL_VERIFY_PIN = BASE_URL + "/verify_pin"
URL_TOKEN = BASE_URL_2 + "/token"

SUCCESS = 1
ERROR = -1


def send_login_otp(fy_id, app_id):
    try:
        r = requests.post(url=URL_SEND_LOGIN_OTP, json={"fy_id": fy_id, "app_id": app_id})
        if r.status_code != 200:
            return [ERROR, r.text]
        result = json.loads(r.text)
        return [SUCCESS, result["request_key"]]
    except Exception as e:
        return [ERROR, e]


def generate_totp(secret):
    try:
        return [SUCCESS, pyotp.TOTP(secret).now()]
    except Exception as e:
        return [ERROR, e]


def verify_totp(request_key, totp):
    try:
        r = requests.post(url=URL_VERIFY_TOTP, json={"request_key": request_key, "otp": totp})
        if r.status_code != 200:
            return [ERROR, r.text]
        result = json.loads(r.text)
        return [SUCCESS, result["request_key"]]
    except Exception as e:
        return [ERROR, e]


def verify_pin(request_key, pin):
    try:
        payload = {"request_key": request_key, "identity_type": "pin", "identifier": pin}
        r = requests.post(url=URL_VERIFY_PIN, json=payload)
        if r.status_code != 200:
            return [ERROR, r.text]
        result = json.loads(r.text)
        return [SUCCESS, result["data"]["access_token"]]
    except Exception as e:
        return [ERROR, e]


def token(fy_id, app_id, redirect_uri, app_type, access_token):
    try:
        payload = {
            "fyers_id": fy_id,
            "app_id": app_id,
            "redirect_uri": redirect_uri,
            "appType": app_type,
            "code_challenge": "",
            "state": "sample_state",
            "scope": "",
            "nonce": "",
            "response_type": "code",
            "create_cookie": True,
        }
        headers = {"Authorization": f"Bearer {access_token}"}
        r = requests.post(url=URL_TOKEN, json=payload, headers=headers)
        if r.status_code != 308:
            return [ERROR, r.text]
        result = json.loads(r.text)
        url = result["Url"]
        auth_code = parse.parse_qs(parse.urlparse(url).query)["auth_code"][0]
        return [SUCCESS, auth_code]
    except Exception as e:
        return [ERROR, e]


def main():
    session = fyersModel.SessionModel(
        client_id=client_id,
        secret_key=SECRET_KEY,
        redirect_uri=REDIRECT_URI,
        response_type="code",
        grant_type="authorization_code",
    )

    print(f"URL to activate APP: {session.generate_authcode()}")

    send_otp_result = send_login_otp(fy_id=FY_ID, app_id=APP_ID_TYPE)
    if send_otp_result[0] != SUCCESS:
        print(f"send_login_otp failed: {send_otp_result[1]}")
        sys.exit(1)

    generate_totp_result = generate_totp(secret=TOTP_KEY)
    if generate_totp_result[0] != SUCCESS:
        print(f"generate_totp failed: {generate_totp_result[1]}")
        sys.exit(1)

    verify_totp_result = [ERROR, "not_attempted"]
    for _ in range(2):
        verify_totp_result = verify_totp(
            request_key=send_otp_result[1],
            totp=generate_totp_result[1],
        )
        if verify_totp_result[0] == SUCCESS:
            break
        tm.sleep(1)

    if verify_totp_result[0] != SUCCESS:
        print(f"verify_totp failed: {verify_totp_result[1]}")
        sys.exit(1)

    verify_pin_result = verify_pin(request_key=verify_totp_result[1], pin=PIN)
    if verify_pin_result[0] != SUCCESS:
        print(f"verify_pin failed: {verify_pin_result[1]}")
        sys.exit(1)

    token_result = token(
        fy_id=FY_ID,
        app_id=APP_ID,
        redirect_uri=REDIRECT_URI,
        app_type=APP_TYPE,
        access_token=verify_pin_result[1],
    )
    if token_result[0] != SUCCESS:
        print(f"token failed: {token_result[1]}")
        sys.exit(1)

    session.set_token(token_result[1])
    response = session.generate_token()

    if response.get("s") == "ERROR":
        print("Cannot login. Check your credentials.")
        sys.exit(1)

    print("Access token generated successfully")
    print(response["access_token"])


if __name__ == "__main__":
    main()
```

## Run

```bash
python main.py
```

If successful, the script prints a fresh API access token.

## Notes

- The API URLs used above are from the source article and may evolve. Verify with official docs if a call starts failing.
- Regenerate tokens securely and rotate credentials if exposed.
