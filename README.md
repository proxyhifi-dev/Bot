# Dual-Mode NIFTY Supertrend Trading Bot

Production-ready Python trading bot with **PAPER/LIVE dual execution**, **manual approval workflow**, **official Fyers OAuth login**, and **risk controls**.

---

## Project Overview

This bot trades **NIFTY 5m candles** using **Supertrend(10,3)** and enforces strict safety:
- Manual approval before entries
- Timed approval auto-rejection (60s)
- Daily trade/loss limits
- Session time filters and square-off
- Concurrency-safe state management across engine + API threads

---

## Architecture Diagram (Text)

```text
run.py
  └─ loads .env, validates/authenticates Fyers token (interactive if needed)
  └─ starts FastAPI (api/main.py)
       ├─ TradingEngine (engine/trading_engine.py)
       │    ├─ ModeManager (PAPER/LIVE)
       │    ├─ RiskManager (1% risk, max trades/losses, time filters)
       │    ├─ Portfolio (open position + trade ledger + pnl)
       │    ├─ SupertrendStrategy(10,3)
       │    ├─ TradeExecutor (paper/live router)
       │    ├─ Approval timeout daemon (60s)
       │    └─ Market evaluation loop (background)
       ├─ FyersAdapter (execution/fyers_adapter.py)
       │    ├─ OAuth login URL + code exchange + token persistence
       │    ├─ token validation (/api/v3/profile)
       │    └─ resilient API calls with exponential backoff
       └─ UI served from ui/index.html
```

---

## Features Implemented

- PAPER and LIVE modes
- Safe mode switching guardrails
- LIVE blocked if auth invalid
- Supertrend(10,3) only
- NIFTY 5m only
- Approval API + UI actions
- 60-second background approval timeout
- Concurrency locks on mutable shared state
- Rate-limit and network retry backoff
- JSON structured logging to `logs/trades.log`
- Backtest with Fyers historical candles

---

## OAuth Setup Guide (Official Manual Flow)

1. Configure `.env` using `.env.example`.
2. Run:
   ```bash
   python run.py
   ```
3. On first run, bot prints Fyers login URL.
4. Open URL in browser and login manually.
5. Copy redirected callback URL (or auth code) and paste into terminal prompt.
6. Bot exchanges code for token and saves token to `FYERS_TOKEN_FILE`.
7. Future runs auto-load token and validate via `/api/v3/profile`.
8. If invalid/expired, manual login is requested again.

> No username/password/PIN/TOTP is automated by code.

---

## How to Run Bot

```bash
pip install -r requirements.txt
cp .env.example .env
# fill credentials
python run.py
```

UI:
- `http://127.0.0.1:8000/`

---

## Mode Switching Guide

- Use UI “Switch Mode” button.
- PAPER → LIVE requires explicit confirmation modal.
- Mode switch is blocked if an open position exists.
- LIVE requires valid Fyers authentication.

---

## Approval Workflow

1. Engine generates pending signal.
2. UI/API shows pending signal and countdown.
3. User can:
   - `POST /approve`
   - `POST /reject`
4. If pending > 60 seconds, background timeout thread auto-rejects.

---

## Risk Rules Explanation

- Strategy: Supertrend(10,3)
- Symbol: `NSE:NIFTY50-INDEX`
- Timeframe: 5 minutes
- Risk per trade: 1% of capital
- Max trades/day: 3
- Stop after 2 losses/day
- No new trades after 14:45
- Force square-off at 15:15

---

## API Documentation

- `GET /signal` – evaluate market and possibly create pending signal
- `POST /approve` – approve pending signal
- `POST /reject` – reject pending signal
- `GET /mode` – current mode
- `POST /mode/switch` – switch mode
- `GET /status` – bot state
- `GET /pnl` – pnl summary
- `GET /trades` – executed trade ledger
- `GET /health` – health + auth status
- `POST /stop` – emergency stop engine

Mode switch payload:
```json
{ "mode": "LIVE", "confirm_live": true }
```

---

## UI Usage Steps

- Observe mode badge and auth status.
- Review pending signal + countdown.
- Approve/reject signals.
- Review trade history and pnl cards.
- Use Emergency STOP to halt engine loop.

---

## Backtest Instructions

```bash
python backtest.py
```

Outputs:
- Total trades
- Win rate
- Net PnL
- Max Drawdown
- Profit Factor

Backtest uses real Fyers historical candles (OAuth required).

---

## Troubleshooting

- **Missing env keys**: ensure `FYERS_CLIENT_ID`, `FYERS_SECRET_KEY`, `FYERS_REDIRECT_URI`.
- **Auth fails**: verify redirect URI matches Fyers app config.
- **429 rate limits**: handled automatically with exponential backoff.
- **LIVE blocked**: validate token (`GET /health`) and ensure no open position.
- **No signals**: strategy may naturally return no signal for current candles.

---

## Known Limitations

- No websocket streaming; polling-based evaluation loop.
- No broker-side open-position reconciliation beyond startup check.
- No advanced portfolio multi-symbol support.

---

## Pending Improvements

- Add websocket market data integration.
- Add persistent database trade journal.
- Add alerting hooks (Slack/Email/PagerDuty).
- Add richer analytics dashboard.

---

## Production Deployment Guide

1. Use Linux host with systemd or container supervisor.
2. Mount `.env` and token file securely.
3. Rotate logs and monitor `logs/trades.log`.
4. Restrict network ingress to trusted operator IPs.
5. Run with reverse proxy (TLS) for UI/API.
6. Maintain periodic backup of token file and logs.
