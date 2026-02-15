import logging
import datetime
import time
from engine.risk import RiskManager
from data_provider import DataProvider
from strategies.supertrend import SupertrendStrategy
from auth import get_fyers_client

# ---------------- CONFIG ---------------- #
SYMBOL = "NSE:NIFTY50-INDEX"
TIMEFRAME = "5"
MAX_TRADES_PER_DAY = 5
DAILY_MAX_LOSS_PERCENT = 2
LIVE_MODE = False  # True = Live Trading | False = Paper Trading
MARKET_START = datetime.time(9, 20)
MARKET_END = datetime.time(15, 15)
# ---------------------------------------- #

logging.basicConfig(
    filename="logs/trading.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

current_position = None
entry_price = None
quantity = 0
trades_today = 0


def is_market_time():
    now = datetime.datetime.now().time()
    return MARKET_START <= now <= MARKET_END


def main():
    global current_position, entry_price, quantity, trades_today

    fyers = get_fyers_client()
    # Set your capital here (should be configurable)
    capital = 100000
    risk_manager = RiskManager(capital, risk_per_trade=0.01, max_daily_loss=DAILY_MAX_LOSS_PERCENT/100)
    data_provider = DataProvider(fyers)
    strategy = SupertrendStrategy()

    logging.info("Bot Started")

    while True:
        try:
            if not is_market_time():
                logging.info("Market Closed. Stopping bot.")
                break

            if trades_today >= MAX_TRADES_PER_DAY:
                logging.info("Max trades reached for today.")
                break

            if risk_manager.hit_daily_loss_limit():
                logging.warning("Daily loss limit hit.")
                break


            try:
                candles = data_provider.get_latest_data(SYMBOL, TIMEFRAME)
                signal = strategy.generate_signal(candles)
                latest_price = candles[-1][4]  # close price
            except Exception as e:
                logging.error(f"Data fetch or signal error: {e}")
                time.sleep(10)
                continue

            # ENTRY LOGIC
            if current_position is None and signal:
                try:
                    stop_loss = latest_price - 50  # Example SL logic
                    quantity = risk_manager.calculate_position_size(latest_price, stop_loss)
                    if quantity <= 0:
                        logging.warning("Position size is zero or negative. Skipping trade.")
                        time.sleep(60)
                        continue
                    entry_price = latest_price
                    current_position = signal
                    trades_today += 1

                    if LIVE_MODE:
                        fyers.place_order({
                            "symbol": SYMBOL,
                            "qty": quantity,
                            "type": 2,
                            "side": 1 if signal == "BUY" else -1,
                            "productType": "INTRADAY"
                        })
                        logging.info(f"LIVE ENTRY: {signal} at {entry_price}")
                    else:
                        logging.info(f"PAPER ENTRY: {signal} at {entry_price}")
                        print(f"PAPER ENTRY: {signal} at {entry_price}")
                except Exception as e:
                    logging.error(f"Trade entry error: {e}")

            # EXIT LOGIC
            elif current_position and signal and signal != current_position:
                try:
                    exit_price = latest_price
                    if current_position == "BUY":
                        pnl = (exit_price - entry_price) * quantity
                    else:
                        pnl = (entry_price - exit_price) * quantity

                    if pnl < 0:
                        risk_manager.update_loss(abs(pnl))

                    logging.info(f"EXIT: {current_position} at {exit_price} | PnL: {pnl}")
                    print(f"EXIT: {current_position} at {exit_price} | PnL: {pnl}")

                    current_position = None
                    entry_price = None
                except Exception as e:
                    logging.error(f"Trade exit error: {e}")

            time.sleep(60)  # Wait 1 minute

        except Exception as e:
            logging.error(f"Error: {e}")
            time.sleep(5)


if __name__ == "__main__":
    main()
