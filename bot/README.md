# Fyers API V3 Production Integration (CLI)

This folder contains a production-safe Python integration for Fyers API V3 with manual OAuth, token persistence, health checks, gateway/rate-limit resilience, and trading API wrappers.

## Project Structure

```text
bot/
├── auth.py
├── fyers_adapter.py
├── health.py
├── run.py
├── utils.py
├── .env.example
├── README.md
├── requirements.txt
├── logs/
└── .secrets/
```

## 1) Create Fyers User App

1. Sign in at Fyers developer portal.
2. Create a new app (API + trading permissions as needed).
3. Copy:
   - **App ID** → `FYERS_CLIENT_ID`
   - **Secret Key** → `FYERS_SECRET_KEY`
4. Add exact Redirect URI in app settings and in `.env` as `FYERS_REDIRECT_URI`.

## 2) Set Redirect URI Correctly

The redirect URI in your app settings and `.env` must match exactly (scheme, host, path, trailing slash behavior).

## 3) Regenerate Secret

In Fyers app settings, use the “regenerate/reset secret” action if your key is exposed or rotated. After regenerating:

- update `.env`
- restart CLI
- perform OAuth again if token is invalid

## 4) Install & Configure

```bash
cd bot
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Fill `.env` values.

## 5) Run

```bash
python run.py
```

## 6) OAuth V3 Flow Used

The CLI follows docsv3 style:

1. Generates login URL using:
   - `GET /api/v3/generate-authcode`
2. You login manually in browser (no automated credentials).
3. Paste redirected URL or `code` into CLI.
4. CLI exchanges code at:
   - `POST /api/v3/token`
5. Access token is saved to `.secrets/fyers_token.json`.
6. Before use, token is validated through:
   - `GET /api/v3/profile`

Authorization header format used for protected APIs:

```text
Authorization: client_id:access_token
```

## 7) Common Error Handling

### 429 (Rate limit)
- Exponential backoff with capped retries.
- No aggressive tight-loop retries.

### 502 / 503 (Gateway/service instability)
- Cooldown delay before retry.
- Circuit breaker opens after repeated failures and pauses trading API calls.
- Health check guard (`GET https://api.fyers.in`) blocks OAuth/trading attempts when service is unhealthy.

## 8) CLI Capabilities

- Authenticate if needed (or auto-use existing valid token)
- Fetch LTP (`/data/quotes`)
- Fetch candles history (`/data/history`)
- Place test order
- Show positions / funds / orderbook

## 9) Logging

Structured JSON logs are written to:

- `logs/bot.log`

Format:

```json
{
  "timestamp": "...",
  "level": "INFO/ERROR",
  "event": "...",
  "details": {"...": "..."}
}
```

## 10) Production Safety Notes

- Do not hardcode credentials.
- Keep `.env` and token files out of source control.
- Use least-privilege runtime user and secure host.
- Validate payload fields against latest Fyers docs before sending live orders.
