from datetime import datetime
import os

import logging

class ExecutionEngine:
    def __init__(self, risk_manager=None, portfolio=None, paper=True):
        self.risk = risk_manager
        self.portfolio = portfolio
        self.paper = paper
        os.makedirs("logs", exist_ok=True)

    def execute_trade(self, symbol, action, entry_price, stop_loss):
        try:
            if self.risk and not self.risk.can_trade():
                logging.warning("❌ Daily loss limit reached.")
                print("❌ Daily loss limit reached.")
                return

            qty = self.risk.calculate_position_size(entry_price, stop_loss) if self.risk else 1

            if qty <= 0:
                logging.warning("❌ Invalid position size.")
                print("❌ Invalid position size.")
                return

            print(f"\n📊 EXECUTING {action} {symbol}")
            print(f"Qty: {qty} | Entry: {entry_price} | SL: {stop_loss}")
            logging.info(f"EXECUTING {action} {symbol} Qty: {qty} | Entry: {entry_price} | SL: {stop_loss}")

            if action == "BUY" and self.portfolio:
                self.portfolio.add_position(symbol, qty, entry_price)

            self.log_trade(symbol, action, qty, entry_price, stop_loss)
        except Exception as e:
            logging.error(f"ExecutionEngine execute_trade error: {e}")

    def close_trade(self, symbol, exit_price):
        try:
            pnl = self.portfolio.close_position(symbol, exit_price) if self.portfolio else 0

            if pnl < 0 and self.risk:
                self.risk.update_loss(abs(pnl))

            print(f"\n📈 Trade Closed | PnL: {pnl}")
            logging.info(f"Trade Closed | {symbol} | PnL: {pnl}")

            with open("logs/trades.log", "a") as f:
                f.write(f"{datetime.now()} | CLOSE | {symbol} | PnL: {pnl}\n")
        except Exception as e:
            logging.error(f"ExecutionEngine close_trade error: {e}")

    def log_trade(self, symbol, action, qty, entry, sl):
        try:
            with open("logs/trades.log", "a") as f:
                f.write(
                    f"{datetime.now()} | {symbol} | {action} | Qty:{qty} | Entry:{entry} | SL:{sl}\n"
                )
        except Exception as e:
            logging.error(f"ExecutionEngine log_trade error: {e}")
