from __future__ import annotations

import datetime
import logging
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

from data_provider import DataProvider
from engine.risk import RiskManager
from execution.fyers_adapter import FyersAdapter
from strategies.supertrend import SupertrendStrategy


SYMBOL = os.getenv("TRADING_SYMBOL", "NSE:NIFTY50-INDEX")
TIMEFRAME = os.getenv("TRADING_TIMEFRAME", "5")
MAX_TRADES_PER_DAY = int(os.getenv("MAX_TRADES_PER_DAY", "5"))
DAILY_MAX_LOSS_PERCENT = float(os.getenv("DAILY_MAX_LOSS_PERCENT", "2"))
LIVE_MODE = os.getenv("LIVE_MODE", "false").strip().lower() == "true"
MARKET_START = datetime.time(9, 15)
MARKET_END = datetime.time(15, 30)
POLL_SECONDS = int(os.getenv("MAIN_LOOP_POLL_SECONDS", "5"))


def setup_logging() -> logging.Logger:
    Path("logs").mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO),
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler("logs/trading.log"),
            logging.StreamHandler(sys.stdout),
        ],
    )
    return logging.getLogger("main_bot")


def is_market_time() -> bool:
    now = datetime.datetime.now().time()
    return MARKET_START <= now <= MARKET_END


def main() -> None:
    load_dotenv()
    logger = setup_logging()

    logger.info("Starting trading bot main loop")

    try:
        fyers = FyersAdapter()
        if not fyers.ensure_authenticated(interactive=not fyers.enable_auto_auth):
            logger.error("Authentication failed. Check FYERS_* credentials in .env")
            return
        logger.info("Authenticated with FYERS successfully")
    except Exception as exc:
        logger.error("Critical authentication error: %s", exc)
        return

    capital = float(os.getenv("CAPITAL", "100000"))
    risk_manager = RiskManager(
        capital,
        risk_per_trade=0.01,
        max_daily_loss=DAILY_MAX_LOSS_PERCENT / 100,
        max_trades_per_day=MAX_TRADES_PER_DAY,
    )
    data_provider = DataProvider(fyers)
    strategy = SupertrendStrategy()

    current_position = None
    entry_price = None
    quantity = 0
    trades_today = 0

    logger.info("Monitoring %s on %sm timeframe", SYMBOL, TIMEFRAME)

    while True:
        try:
            if not is_market_time():
                logger.info("Market is closed. Waiting...")
                time.sleep(60)
                continue

            if trades_today >= MAX_TRADES_PER_DAY:
                logger.info("Max trades reached for today. Stopping loop.")
                break

            if risk_manager.hit_daily_loss_limit():
                logger.warning("Daily loss limit hit. Stopping loop.")
                break

            try:
                candles = data_provider.get_latest_data(SYMBOL, TIMEFRAME)
                latest_close = candles[-1][4]
                signal = strategy.generate_signal(candles)
            except Exception as exc:
                logger.error("Data/strategy error: %s", exc)
                time.sleep(POLL_SECONDS)
                continue

            if current_position is None and signal:
                stop_loss = latest_close - 50 if signal == "BUY" else latest_close + 50
                quantity = risk_manager.calculate_position_size(latest_close, stop_loss)

                if quantity > 0:
                    entry_price = latest_close
                    current_position = signal
                    trades_today += 1

                    if LIVE_MODE:
                        order_response = fyers.place_order({
                            "symbol": SYMBOL,
                            "qty": quantity,
                            "type": 2,
                            "side": 1 if signal == "BUY" else -1,
                            "productType": "INTRADAY",
                            "validity": "DAY",
                        })
                        logger.info("LIVE ENTRY placed: %s", order_response)
                    else:
                        logger.info("PAPER ENTRY: %s %s @ %s", signal, quantity, entry_price)

            elif current_position and signal and signal != current_position:
                exit_price = latest_close
                pnl = (
                    (exit_price - entry_price) * quantity
                    if current_position == "BUY"
                    else (entry_price - exit_price) * quantity
                )

                if LIVE_MODE:
                    exit_side = -1 if current_position == "BUY" else 1
                    fyers.place_order({
                        "symbol": SYMBOL,
                        "qty": quantity,
                        "type": 2,
                        "side": exit_side,
                        "productType": "INTRADAY",
                        "validity": "DAY",
                    })

                if pnl < 0:
                    risk_manager.update_loss(abs(pnl))

                logger.info("EXIT: %s @ %s | PnL %.2f", current_position, exit_price, pnl)
                current_position = None
                entry_price = None
                quantity = 0

            time.sleep(POLL_SECONDS)

        except KeyboardInterrupt:
            logger.info("Bot stopped manually")
            break
        except Exception as exc:
            logger.error("Unexpected loop error: %s", exc)
            time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
