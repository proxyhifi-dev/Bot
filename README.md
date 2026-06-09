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

## Quick Answer: authentication + run + what you get

### 1) How authentication works

You have **2 authentication modes**:

- **Manual (default)**
  - Bot prints login URL.
  - You login in browser.
  - You paste callback URL/code in terminal.
  - Bot stores `access_token` in `FYERS_TOKEN_FILE`.

- **Auto (optional)**
  - Set `FYERS_AUTO_AUTH=true`.
  - Provide `FYERS_USER_ID`, `FYERS_PIN`, `FYERS_TOTP_SECRET`.
  - Bot generates auth code automatically and exchanges token.

In both modes, token is validated via FYERS profile API before LIVE actions.

### 2) How to run

```bash
pip install -r requirements.txt
cp .env.example .env
# fill all FYERS_* values in .env
python run.py
```

Open UI at:

```text
http://127.0.0.1:8000/
```

### 3) What you get

- Dual mode trading: `PAPER` + `LIVE`
- Supertrend strategy execution loop
- Manual approve/reject workflow for entries
- Risk controls (max trades/day, stop after losses, session cutoffs)
- Health/mode/status/PnL APIs
- Trade logs persisted to `logs/trades.log`

### 4) What it has (main APIs)

- `GET /health` → auth + service health
- `GET /status` → current runtime status
- `GET /signal` → current evaluated signal
- `POST /approve` / `POST /reject` → action pending signal
- `POST /mode/switch` → switch PAPER/LIVE
- `GET /pnl` and `GET /trades` → performance + trade ledger

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

> Default mode uses manual login.
> Optional: set `FYERS_AUTO_AUTH=true` with `FYERS_USER_ID`, `FYERS_PIN`, and `FYERS_TOTP_SECRET` to enable automated auth-code generation (similar to the `fyers-api-access-token-v3` flow).

---

## Automated OAuth (Optional)

If you want non-interactive startup:

```bash
FYERS_AUTO_AUTH=true
FYERS_USER_ID=<your_fyers_id>
FYERS_PIN=<4_digit_pin>
FYERS_TOTP_SECRET=<base32_totp_secret>
```

Then run normally (`python run.py`). The bot will:
1. Request login OTP from Fyers auth API
2. Generate TOTP locally
3. Verify PIN to get a temporary bearer token
4. Request auth code URL
5. Exchange auth code for access token and persist it

Manual flow remains available as fallback if `FYERS_AUTO_AUTH` is false.

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

## Additional Guides

- Fyers TOTP auto-login walkthrough: `docs/fyers_totp_auto_login_guide.md`















INFO:     Waiting for application startup.
2026-06-09 10:10:29  INFO      state_manager               State DB initialized path=data\runtime_state.db
2026-06-09 10:10:29  INFO      state_manager               Redis disabled (USE_REDIS=False)
2026-06-09 10:10:29  INFO      state_manager               Applying automatic intraday rollover | old=2026-06-08 new=2026-06-09
2026-06-09 10:10:30  INFO      trade_store                 TradeStore loaded 0 trades pnl=0.00
2026-06-09 10:10:30  INFO      iron_condor_strategy        IronCondorStrategy initialized | entry=09:30:00-10:30:00 exit=15:00:00 target=0.500 sl=1.50 extreme=2.50 short_distance=400 wing=150 min_entry=40.00 proximity_exit=True ratio=0.40
2026-06-09 10:10:30  INFO      trading_engine              Iron Condor strategy enabled in TradingEngine
2026-06-09 10:10:30  INFO      trading_engine              TradingEngine initialized mode=PAPER broker_connected=True paper_mode_use_broker=True
2026-06-09 10:10:30  INFO      main                        Lords Bot starting — mode=PAPER strategy=IRON_CONDOR
2026-06-09 10:10:30  INFO      startup_manager             Starting safe startup...
2026-06-09 10:10:30  INFO      startup_manager             Startup mode resolved | mode=paper is_live=False paper_mode_use_broker=True
2026-06-09 10:10:30  INFO      startup_manager             Initializing core components...
2026-06-09 10:10:30  INFO      state_manager               State DB initialized path=data\runtime_state.db
2026-06-09 10:10:30  INFO      state_manager               Redis disabled (USE_REDIS=False)
2026-06-09 10:10:30  INFO      trade_store                 TradeStore loaded 0 trades pnl=0.00
2026-06-09 10:10:30  INFO      startup_manager             Core components initialized
2026-06-09 10:10:30  INFO      startup_manager             Initializing broker...
2026-06-09 10:10:30  INFO      startup_manager             Logging in to broker...
2026-06-09 10:10:30  INFO      samco_client                SAMCO login user=DB4***
2026-06-09 10:10:32  INFO      samco_client                SAMCO login successful
2026-06-09 10:10:32  INFO      startup_manager             Broker login successful
2026-06-09 10:10:32  INFO      startup_manager             Initializing trading engine...
2026-06-09 10:10:32  INFO      iron_condor_strategy        IronCondorStrategy initialized | entry=09:30:00-10:30:00 exit=15:00:00 target=0.500 sl=1.50 extreme=2.50 short_distance=400 wing=150 min_entry=40.00 proximity_exit=True ratio=0.40
2026-06-09 10:10:32  INFO      trading_engine              Iron Condor strategy enabled in TradingEngine
2026-06-09 10:10:32  INFO      trading_engine              TradingEngine initialized mode=PAPER broker_connected=True paper_mode_use_broker=True
2026-06-09 10:10:32  INFO      startup_manager             Trading engine ready
2026-06-09 10:10:32  INFO      startup_manager             Fetching positions & orders...
2026-06-09 10:10:33  INFO      startup_manager             Broker sync | positions=0 orders=0
2026-06-09 10:10:33  INFO      startup_manager             Fetching initial spot price...
2026-06-09 10:10:33  INFO      startup_manager             Spot price: 23169.95
2026-06-09 10:10:33  INFO      startup_manager             Paper mode startup: trading auto-resumed
2026-06-09 10:10:33  INFO      startup_manager             SAFE STARTUP COMPLETE
2026-06-09 10:10:33  INFO      startup_manager             BOT READY
2026-06-09 10:10:33  INFO      market_scheduler            SCHEDULER START CALLED
2026-06-09 10:10:33  INFO      market_scheduler            Starting Lords Bot (Iron Condor) — mode=PAPER strategy=IRON_CONDOR
2026-06-09 10:10:33  INFO      state_manager               State loaded from DB
2026-06-09 10:10:33  INFO      market_scheduler            State check: spot_price=23169.95 trading_enabled=True active_trade=False last_ic_month=6 last_trade_date=2026-06-04 trade_count=0
2026-06-09 10:10:33  INFO      event_bus                   EventBus started
2026-06-09 10:10:33  INFO      samco_client                SAMCO login user=DB4***
2026-06-09 10:10:34  INFO      samco_client                SAMCO login successful
2026-06-09 10:10:34  INFO      market_scheduler            All scheduler tasks started (7 tasks)
2026-06-09 10:10:34  INFO      market_scheduler            MARKET LOOP TASK STARTED
2026-06-09 10:10:34  INFO      risk_manager                RiskManager listening for SIGNAL events
2026-06-09 10:10:34  INFO      trading_engine              TradingEngine started
2026-06-09 10:10:34  INFO      market_scheduler            DAILY WATCHER TASK STARTED
2026-06-09 10:10:34  INFO      market_scheduler            Scheduler rejection watcher started
2026-06-09 10:10:34  INFO      telegram_notifier           Telegram notifier disabled (TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID not set)
INFO:     Application startup complete.
2026-06-09 10:10:34  INFO      reconciliation              ℹ️ PAPER MODE: Broker reconciliation bypassed.
2026-06-09 10:10:34  INFO      trading_engine              TradingEngine listening for RISK_APPROVED events
2026-06-09 10:10:34  INFO      market_scheduler            Task completed: telegram-notifier
2026-06-09 10:10:34  INFO      market_scheduler            Startup reconciliation completed: {'timestamp': '2026-06-09T10:10:34.151373+05:30', 'issues_found': 0, 'actions_taken': [], 'status': 'ok'}
2026-06-09 10:10:34  INFO      market_scheduler            Task completed: reconcile-startup
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
2026-06-09 10:10:34  INFO      market_scheduler            IC expiry day: using next week expiry on 2026-06-09
2026-06-09 10:10:34  INFO      market_scheduler            IC gate passed: one_per_day=True monthly_only=False time=10:10:34 spot=23168.65 iv_age=0s
2026-06-09 10:10:34  INFO      market_scheduler            IRON_CONDOR entry signal emitted spot=23168.65
2026-06-09 10:10:34  INFO      risk_manager                RiskManager received SIGNAL payload={'signal': 'IRON_CONDOR', 'spot_price': 23168.65, 'size_label': 'FULL'}
2026-06-09 10:10:34  INFO      risk_manager                RiskManager evaluating payload={'signal': 'IRON_CONDOR', 'spot_price': 23168.65, 'size_label': 'FULL'} trading_enabled=True active_trade=False trade_count=0 daily_pnl=0.0
2026-06-09 10:10:34  INFO      risk_manager                RISK_APPROVED signal=IRON_CONDOR size=FULL spot=23168.65
2026-06-09 10:10:34  INFO      trading_engine              TradingEngine received event: {'signal': 'IRON_CONDOR', 'spot_price': 23168.65, 'size_label': 'FULL'}
2026-06-09 10:10:34  INFO      trading_engine              SIGNAL RECEIVED raw=IRON_CONDOR size=FULL spot=23168.65
2026-06-09 10:10:34  INFO      trading_engine              SIGNAL MAPPED IRON_CONDOR -> IRON_CONDOR
2026-06-09 10:10:34  INFO      trading_engine              IC entry check started spot=23168.65 iv=0.1605 time=2026-06-09T10:10:34.478092+05:30
2026-06-09 10:10:34  INFO      iron_condor_strategy        IC expiry day: using next week expiry current=2026-06-09 next=2026-06-16
2026-06-09 10:10:34  INFO      iron_condor_strategy        IC entry allowed: expiry day 2026-06-09 using next week expiry 2026-06-16
2026-06-09 10:10:34  INFO      iron_condor_strategy        Iron Condor entry allowed
2026-06-09 10:10:34  INFO      trading_engine              IC can_enter_cycle=True
2026-06-09 10:10:34  INFO      iron_condor_strategy        IC expiry day: using next week expiry current=2026-06-09 next=2026-06-16
2026-06-09 10:10:34  INFO      iron_condor_strategy        Delta-strikes target=0.16 SC=23700(Δ0.156) SP=22650(Δ0.152) LC=23850 LP=22500
2026-06-09 10:10:34  INFO      trading_engine              IC delta-strikes spot=23168.65 iv=0.1605 dte=7 strikes={'short_call': 23700, 'long_call': 23850, 'short_put': 22650, 'long_put': 22500, 'call_width': 150, 'put_width': 150}
2026-06-09 10:10:34  INFO      trading_engine              IC expected-move filter passed diag={'spot': 23168.65, 'short_distance': 531.0, 'live_iv': 0.1605, 'expected_move': 253.03, 'min_safety_buffer_points': 50.0, 'actual_margin': 277.97}
2026-06-09 10:10:34  INFO      trading_engine              IC score gate inputs: trend_strength=0.000 iv_rank=N/A (insufficient history)
2026-06-09 10:10:34  INFO      iron_condor_strategy        Entry score=80.0 verdict=excellent pop=72.5% theta_vega=1.1464 iv=16.1% trend=0.00 rank=None
2026-06-09 10:10:34  INFO      trading_engine              IC entry score passed score=80.0 verdict=excellent pop=72.5%
2026-06-09 10:10:34  INFO      trading_engine              IC entry using expiry=2026-06-16
2026-06-09 10:10:34  INFO      trading_engine              IC SYMBOL LOOKUP: strike=22500 type=PE expiry=2026-06-16
2026-06-09 10:10:34  INFO      trading_engine              IC SYMBOL RESOLVED: NIFTY16JUN2622500PE (snap_diff=0.0) cache_key=22500_PE_2026-06-16_2026-06-09
2026-06-09 10:10:34  INFO      trading_engine              IC SYMBOL LOOKUP: strike=22650 type=PE expiry=2026-06-16
2026-06-09 10:10:36  INFO      market_scheduler            IC expiry day: using next week expiry on 2026-06-09
2026-06-09 10:10:36  INFO      market_scheduler            IC gate blocked: cooldown active last_signal_age=2s
2026-06-09 10:10:36  ERROR     trading_engine              IC option chain empty: strike=22650 type=PE
2026-06-09 10:10:36  ERROR     trading_engine              Failed to resolve IC leg symbol for short_put strike=22650 type=PE expiry=2026-06-16
2026-06-09 10:10:36  ERROR     trading_engine              Failed to build IC quote snapshot legs - skipping entry
2026-06-09 10:10:37  INFO      market_scheduler            IC expiry day: using next week expiry on 2026-06-09
2026-06-09 10:10:37  INFO      market_scheduler            IC gate blocked: cooldown active last_signal_age=3s
2026-06-09 10:10:38  INFO      market_scheduler            IC expiry day: using next week expiry on 2026-06-09
2026-06-09 10:10:38  INFO      market_scheduler            IC gate blocked: cooldown active last_signal_age=4s
2026-06-09 10:10:39  INFO      market_scheduler            IC expiry day: using next week expiry on 2026-06-09
2026-06-09 10:10:39  INFO      market_scheduler            IC gate blocked: cooldown active last_signal_age=5s
2026-06-09 10:10:40  INFO      market_scheduler            IC expiry day: using next week expiry on 2026-06-09
2026-06-09 10:10:40  INFO      market_scheduler            IC gate blocked: cooldown active last_signal_age=6s
2026-06-09 10:10:41  INFO      market_scheduler            IC expiry day: using next week expiry on 2026-06-09
2026-06-09 10:10:41  INFO      market_scheduler            IC gate blocked: cooldown active last_signal_age=7s
2026-06-09 10:10:42  INFO      market_scheduler            IC expiry day: using next week expiry on 2026-06-09
2026-06-09 10:10:42  INFO      market_scheduler            IC gate blocked: cooldown active last_signal_age=8s
2026-06-09 10:10:43  INFO      market_scheduler            IC expiry day: using next week expiry on 2026-06-09
2026-06-09 10:10:43  INFO      market_scheduler            IC gate blocked: cooldown active last_signal_age=9s
2026-06-09 10:10:44  INFO      market_scheduler            IC expiry day: using next week expiry on 2026-06-09
2026-06-09 10:10:44  INFO      market_scheduler            IC gate blocked: cooldown active last_signal_age=10s
2026-06-09 10:10:45  INFO      market_scheduler            IC expiry day: using next week expiry on 2026-06-09
2026-06-09 10:10:45  INFO      market_scheduler            IC gate blocked: cooldown active last_signal_age=11s
2026-06-09 10:10:46  INFO      market_scheduler            IC expiry day: using next week expiry on 2026-06-09
2026-06-09 10:10:46  INFO      market_scheduler            IC gate blocked: cooldown active last_signal_age=12s
2026-06-09 10:10:47  INFO      market_scheduler            IC expiry day: using next week expiry on 2026-06-09
2026-06-09 10:10:47  INFO      market_scheduler            IC gate blocked: cooldown active last_signal_age=13s
2026-06-09 10:10:48  INFO      market_scheduler            IC expiry day: using next week expiry on 2026-06-09
2026-06-09 10:10:48  INFO      market_scheduler            IC gate blocked: cooldown active last_signal_age=14s
2026-06-09 10:10:49  INFO      market_scheduler            IC expiry day: using next week expiry on 2026-06-09
2026-06-09 10:10:49  INFO      market_scheduler            IC gate blocked: cooldown active last_signal_age=15s
2026-06-09 10:10:50  INFO      market_scheduler            IC expiry day: using next week expiry on 2026-06-09
2026-06-09 10:10:50  INFO      market_scheduler            IC gate blocked: cooldown active last_signal_age=17s
2026-06-09 10:10:52  INFO      market_scheduler            IC expiry day: using next week expiry on 2026-06-09
2026-06-09 10:10:52  INFO      market_scheduler            IC gate blocked: cooldown active last_signal_age=18s
2026-06-09 10:10:53  INFO      market_scheduler            IC expiry day: using next week expiry on 2026-06-09
2026-06-09 10:10:53  INFO      market_scheduler            IC gate blocked: cooldown active last_signal_age=19s
2026-06-09 10:10:54  INFO      market_scheduler            IC expiry day: using next week expiry on 2026-06-09
2026-06-09 10:10:54  INFO      market_scheduler            IC gate blocked: cooldown active last_signal_age=20s
2026-06-09 10:10:55  INFO      market_scheduler            IC expiry day: using next week expiry on 2026-06-09
2026-06-09 10:10:55  INFO      market_scheduler            IC gate blocked: cooldown active last_signal_age=21s
2026-06-09 10:10:56  INFO      market_scheduler            IC expiry day: using next week expiry on 2026-06-09
2026-06-09 10:10:56  INFO      market_scheduler            IC gate blocked: cooldown active last_signal_age=22s
2026-06-09 10:10:57  INFO      market_scheduler            IC expiry day: using next week expiry on 2026-06-09
2026-06-09 10:10:57  INFO      market_scheduler            IC gate blocked: cooldown active last_signal_age=23s
2026-06-09 10:10:58  INFO      market_scheduler            IC expiry day: using next week expiry on 2026-06-09
2026-06-09 10:10:58  INFO      market_scheduler            IC gate blocked: cooldown active last_signal_age=24s
2026-06-09 10:10:59  INFO      market_scheduler            IC expiry day: using next week expiry on 2026-06-09
2026-06-09 10:10:59  INFO      market_scheduler            IC gate blocked: cooldown active last_signal_age=25s
2026-06-09 10:11:00  INFO      market_scheduler            IC expiry day: using next week expiry on 2026-06-09
2026-06-09 10:11:00  INFO      market_scheduler            IC gate blocked: cooldown active last_signal_age=26s
2026-06-09 10:11:01  INFO      market_scheduler            IC expiry day: using next week expiry on 2026-06-09
2026-06-09 10:11:01  INFO      market_scheduler            IC gate blocked: cooldown active last_signal_age=27s
2026-06-09 10:11:02  INFO      market_scheduler            IC expiry day: using next week expiry on 2026-06-09
2026-06-09 10:11:02  INFO      market_scheduler            IC gate blocked: cooldown active last_signal_age=28s
2026-06-09 10:11:03  INFO      market_scheduler            IC expiry day: using next week expiry on 2026-06-09
2026-06-09 10:11:03  INFO      market_scheduler            IC gate blocked: cooldown active last_signal_age=29s
2026-06-09 10:11:04  INFO      market_scheduler            IC expiry day: using next week expiry on 2026-06-09
2026-06-09 10:11:04  INFO      market_scheduler            IC gate blocked: cooldown active last_signal_age=30s
2026-06-09 10:11:05  INFO      market_scheduler            IC expiry day: using next week expiry on 2026-06-09
2026-06-09 10:11:05  INFO      market_scheduler            IC gate blocked: cooldown active last_signal_age=31s
2026-06-09 10:11:06  INFO      market_scheduler            IC expiry day: using next week expiry on 2026-06-09
2026-06-09 10:11:06  INFO      market_scheduler            IC gate blocked: cooldown active last_signal_age=32s
INFO:     127.0.0.1:58855 - "GET / HTTP/1.1" 200 OK
INFO:     127.0.0.1:58855 - "GET /static/styles.css?v=7 HTTP/1.1" 200 OK
INFO:     127.0.0.1:58855 - "GET /static/dashboard.js?v=14 HTTP/1.1" 200 OK
2026-06-09 10:11:08  INFO      market_scheduler            IC expiry day: using next week expiry on 2026-06-09
2026-06-09 10:11:08  INFO      market_scheduler            IC gate blocked: cooldown active last_signal_age=34s
INFO:     127.0.0.1:58855 - "GET /favicon.ico HTTP/1.1" 404 Not Found
2026-06-09 10:11:09  INFO      market_scheduler            IC expiry day: using next week expiry on 2026-06-09
2026-06-09 10:11:09  INFO      market_scheduler            IC gate blocked: cooldown active last_signal_age=35s
INFO:     127.0.0.1:61285 - "GET /api/dashboard HTTP/1.1" 200 OK
INFO:     127.0.0.1:56788 - "GET /api/iron-condor/stats HTTP/1.1" 200 OK
INFO:     127.0.0.1:61266 - "GET /api/analytics HTTP/1.1" 200 OK
INFO:     127.0.0.1:61266 - "GET /api/dashboard HTTP/1.1" 200 OK
2026-06-09 10:11:10  INFO      market_scheduler            IC expiry day: using next week expiry on 2026-06-09
2026-06-09 10:11:10  INFO      market_scheduler            IC gate blocked: cooldown active last_signal_age=36s
INFO:     127.0.0.1:61266 - "GET / HTTP/1.1" 200 OK
INFO:     127.0.0.1:61266 - "GET /api/dashboard HTTP/1.1" 200 OK
INFO:     127.0.0.1:56788 - "GET /api/iron-condor/stats HTTP/1.1" 200 OK
INFO:     127.0.0.1:61285 - "GET /api/analytics HTTP/1.1" 200 OK
2026-06-09 10:11:11  INFO      market_scheduler            IC expiry day: using next week expiry on 2026-06-09
2026-06-09 10:11:11  INFO      market_scheduler            IC gate blocked: cooldown active last_signal_age=37s
2026-06-09 10:11:12  INFO      market_scheduler            IC expiry day: using next week expiry on 2026-06-09
2026-06-09 10:11:12  INFO      market_scheduler            IC gate blocked: cooldown active last_signal_age=38s
INFO:     127.0.0.1:61285 - "GET /api/dashboard HTTP/1.1" 200 OK
2026-06-09 10:11:13  INFO      market_scheduler            IC expiry day: using next week expiry on 2026-06-09
2026-06-09 10:11:13  INFO      market_scheduler            IC gate blocked: cooldown active last_signal_age=39s
2026-06-09 10:11:14  INFO      market_scheduler            IC expiry day: using next week expiry on 2026-06-09
2026-06-09 10:11:14  INFO      market_scheduler            IC gate blocked: cooldown active last_signal_age=40s
INFO:     127.0.0.1:61285 - "GET /api/dashboard HTTP/1.1" 200 OK
2026-06-09 10:11:15  INFO      market_scheduler            IC expiry day: using next week expiry on 2026-06-09
2026-06-09 10:11:15  INFO      market_scheduler            IC gate blocked: cooldown active last_signal_age=41s
INFO:     127.0.0.1:61285 - "GET /api/iron-condor/stats HTTP/1.1" 200 OK
INFO:     127.0.0.1:61285 - "GET /api/dashboard HTTP/1.1" 200 OK
2026-06-09 10:11:16  INFO      market_scheduler            IC expiry day: using next week expiry on 2026-06-09
2026-06-09 10:11:16  INFO      market_scheduler            IC gate blocked: cooldown active last_signal_age=42s
2026-06-09 10:11:17  INFO      market_scheduler            IC expiry day: using next week expiry on 2026-06-09
2026-06-09 10:11:17  INFO      market_scheduler            IC gate blocked: cooldown active last_signal_age=43s
INFO:     127.0.0.1:61285 - "GET /api/dashboard HTTP/1.1" 200 OK
2026-06-09 10:11:18  INFO      market_scheduler            IC expiry day: using next week expiry on 2026-06-09
2026-06-09 10:11:18  INFO      market_scheduler            IC gate blocked: cooldown active last_signal_age=44s
2026-06-09 10:11:19  INFO      market_scheduler            IC expiry day: using next week expiry on 2026-06-09
2026-06-09 10:11:19  INFO      market_scheduler            IC gate blocked: cooldown active last_signal_age=45s
2026-06-09 10:11:20  INFO      market_scheduler            IC expiry day: using next week expiry on 2026-06-09
2026-06-09 10:11:20  INFO      market_scheduler            IC gate blocked: cooldown active last_signal_age=47s
2026-06-09 10:11:22  INFO      market_scheduler            IC expiry day: using next week expiry on 2026-06-09
2026-06-09 10:11:22  INFO      market_scheduler            IC gate blocked: cooldown active last_signal_age=48s
2026-06-09 10:11:23  INFO      market_scheduler            IC expiry day: using next week expiry on 2026-06-09
2026-06-09 10:11:23  INFO      market_scheduler            IC gate blocked: cooldown active last_signal_age=49s
2026-06-09 10:11:24  INFO      market_scheduler            IC expiry day: using next week expiry on 2026-06-09
2026-06-09 10:11:24  INFO      market_scheduler            IC gate blocked: cooldown active last_signal_age=50s
2026-06-09 10:11:25  INFO      market_scheduler            IC expiry day: using next week expiry on 2026-06-09
2026-06-09 10:11:25  INFO      market_scheduler            IC gate blocked: cooldown active last_signal_age=51s
2026-06-09 10:11:26  INFO      market_scheduler            IC expiry day: using next week expiry on 2026-06-09
2026-06-09 10:11:26  INFO      market_scheduler            IC gate blocked: cooldown active last_signal_age=52s
2026-06-09 10:11:27  INFO      market_scheduler            IC expiry day: using next week expiry on 2026-06-09
2026-06-09 10:11:27  INFO      market_scheduler            IC gate blocked: cooldown active last_signal_age=53s
2026-06-09 10:11:28  INFO      market_scheduler            IC expiry day: using next week expiry on 2026-06-09
2026-06-09 10:11:28  INFO      market_scheduler            IC gate blocked: cooldown active last_signal_age=54s
INFO:     Shutting down
INFO:     Waiting for application shutdown.
2026-06-09 10:11:28  INFO      main                        Lords Bot shutting down
2026-06-09 10:11:28  INFO      market_scheduler            Stopping Lords Bot scheduler
2026-06-09 10:11:28  INFO      event_bus                   EventBus stopped
2026-06-09 10:11:28  INFO      market_scheduler            Task cancelled: market-loop
2026-06-09 10:11:28  INFO      market_scheduler            Task cancelled: risk-manager
2026-06-09 10:11:28  INFO      trading_engine              TradingEngine cancelled (normal shutdown)
2026-06-09 10:11:28  INFO      market_scheduler            Task cancelled: trading-engine
2026-06-09 10:11:28  INFO      market_scheduler            Task cancelled: daily-reset
2026-06-09 10:11:28  INFO      market_scheduler            Task cancelled: reconciler
2026-06-09 10:11:28  INFO      market_scheduler            Task cancelled: rejection-watcher
2026-06-09 10:11:28  INFO      market_scheduler            Scheduler stopped
INFO:     Application shutdown complete.
INFO:     Finished server process [9608]
PS C:\Users\bollu\github\lords> 
