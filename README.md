# Dual-Mode NIFTY Trading System (PAPER + LIVE)

Production-ready algorithmic trading system with **safe one-button mode switching** between:

- **PAPER mode** (simulated execution at real LTP)
- **LIVE mode** (real broker order execution via Fyers)

---

## Features

- Single global trading mode: `PAPER` / `LIVE`
- One-button mode switch in Web UI with confirmations
- Mode switch blocked if position is open
- LIVE switch requires explicit confirmation + auth validation
- Supertrend strategy on NIFTY 5-minute data (`Supertrend(10,3)`)
- Approval workflow (`Approve` / `Reject`) before order entry
- Risk controls:
  - 1% risk per trade
  - max 3 trades/day
  - stop after 2 losses
  - no new entries after 2:45 PM
  - force square-off at 3:15 PM
- Trade, signal, approval, execution, exit, pnl, mode-change logging
- Backtest using historical Fyers data with performance metrics

---

## Project Structure

```
api/main.py                 FastAPI app + required endpoints
engine/mode.py              TradingMode enum + mode-switch guardrails
engine/trading_engine.py    Main orchestration (signals/risk/execution)
engine/execution.py         Paper + Live execution router
execution/fyers_adapter.py  Fyers OAuth + market/order APIs
engine/risk.py              Risk/time window controls
engine/portfolio.py         Position state, PnL, drawdown, win-rate
strategies/supertrend.py    Supertrend(10,3) signal generation
ui/index.html               Dashboard with one-button mode toggle
backtest.py                 Independent backtest runner
.env.example                Environment template
```

---

## Prerequisites

- Python 3.10+
- Fyers app credentials (for LIVE mode)
- Network connectivity to Fyers APIs

---

## Setup

1. **Clone and enter repo**

```bash
git clone <repo_url>
cd Bot
```

2. **Create virtual environment**

```bash
python -m venv .venv
source .venv/bin/activate
```

3. **Install dependencies**

```bash
pip install -r requirements.txt
```

4. **Configure environment**

```bash
cp .env.example .env
```

Then set values in `.env`:

- `FYERS_CLIENT_ID`
- `FYERS_SECRET_KEY`
- `FYERS_REDIRECT_URI`
- `FYERS_ACCESS_TOKEN` (or fetch via OAuth flow)
- `FYERS_BASE_URL` (default provided)
- `TRADING_SYMBOL` (default NIFTY index)
- `CAPITAL`

---

## Run the API + UI

```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000
```

Open UI:

- `http://127.0.0.1:8000/`

---


## Fyers Authentication (Step-by-step)

1. Set in `.env`:
   - `FYERS_CLIENT_ID`
   - `FYERS_SECRET_KEY`
   - `FYERS_REDIRECT_URI=http://127.0.0.1:8000/auth/callback`

2. Start app:

```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000
```

3. Open in browser:

```
http://127.0.0.1:8000/auth/login
```

4. Login/consent in Fyers. Fyers will redirect to `/auth/callback` with `code`.

5. Server exchanges code for access token and stores `FYERS_ACCESS_TOKEN` into `.env` automatically.

6. Verify auth:

```
curl http://127.0.0.1:8000/auth/status
```

Expected: `token_valid: true` before switching to LIVE mode.

---

## How Mode Switching Works

### PAPER → LIVE

Allowed only if all are true:

- No open position
- `confirm_live=true`
- Fyers auth token is valid

When LIVE is activated, system writes an elevated risk warning in logs.

### LIVE → PAPER

- Immediate switch allowed only if no open position.

### Block conditions

- If open position exists, mode switch is rejected.

---

## UI Usage

Dashboard supports:

- Current mode badge (`PAPER MODE` warning style / `LIVE MODE` alert style)
- One-button mode toggle with confirmation dialogs
- Bot status
- Current position
- Today PnL
- Pending signal
- Approval countdown
- Trade history
- Approve / Reject buttons
- Auto-refresh every 3 seconds

---

## API Endpoints

- `GET /signal` → Evaluate market and create pending signal if conditions pass
- `POST /approve` → Approve pending signal and execute entry
- `POST /reject` → Reject pending signal
- `GET /status` → Runtime status snapshot
- `GET /pnl` → PnL summary
- `GET /mode` → Current trading mode
- `POST /mode/switch` → Switch mode safely
- `GET /trades` → Trade ledger
- `GET /health` → Health + auth status (in LIVE)
- `GET /auth/login` → Start OAuth login (redirect to Fyers)
- `GET /auth/callback` → Exchange auth code and save token to `.env`
- `GET /auth/status` → Check OAuth configuration/token validity

### Mode switch payload example

```json
{
  "mode": "LIVE",
  "confirm_live": true
}
```

---

## Paper vs Live Execution

### PAPER

- Uses **real market LTP**
- Simulates fills at LTP
- Applies same strategy/risk/time constraints
- Tracks entry/exit/PnL/drawdown/win-rate
- Trades/logs marked as PAPER

### LIVE

- Real order placement via Fyers
- Token validation required
- Retry handling for transient/rate-limit errors
- Duplicate order guard
- Position sync support

---

## Backtest

Run:

```bash
python backtest.py
```

Outputs:

- Total Trades
- Win Rate
- Net PnL
- Max Drawdown
- Profit Factor

Backtest is independent of runtime mode switch state.

---

## Operational Safety Checklist (Before LIVE)

1. Run in PAPER mode for multiple sessions.
2. Verify signals, approvals, SL/Target exits, and PnL accounting.
3. Verify mode switch blocks while position is open.
4. Validate Fyers token and profile API.
5. Confirm no duplicate order behavior under retries.
6. Keep monitoring logs during first LIVE activation.

---

## Testing

Run unit tests:

```bash
python -m pytest -q
```

Compile check:

```bash
python -m compileall api engine execution strategies backtest.py
```

---

## Notes

- This system routes execution strictly by global mode.
- Never enable LIVE without valid broker auth and dry-run validation in PAPER.
- Market/API/network failures should be monitored with proper alerting in production deployment.
