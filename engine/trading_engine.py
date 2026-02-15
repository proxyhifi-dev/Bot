
from queue import Queue
from engine.events import MarketEvent
from strategies.supertrend import SupertrendStrategy
from engine.execution import ExecutionEngine
import logging


class TradingEngine:
    def __init__(self, option_chain_provider=None):
        self.event_bus = Queue()
        self.strategy = SupertrendStrategy()
        self.execution = ExecutionEngine()
        self.option_chain_provider = option_chain_provider

    def on_market_data(self, symbol, price):
        self.event_bus.put(MarketEvent(symbol, price))

    def run(self):
        while not self.event_bus.empty():
            event = self.event_bus.get()
            try:
                # Market Data Event
                if event.__class__.__name__ == "MarketEvent":
                    option_chain = None
                    if self.option_chain_provider:
                        try:
                            option_chain = self.option_chain_provider(event.symbol)
                        except Exception as e:
                            logging.error(f"Option chain fetch error: {e}")
                    self.strategy.generate_signal(event, self.event_bus, option_chain=option_chain)

                # Signal Event
                elif event.__class__.__name__ == "SignalEvent":
                    if event.action == "BUY":
                        self.execution.execute_trade(
                            symbol=event.symbol,
                            action="BUY",
                            entry_price=event.price,
                            stop_loss=event.price - 50
                        )
                        logging.info(f"Trade executed: BUY {event.symbol} at {event.price}")
                    elif event.action == "EXIT":
                        self.execution.close_trade(
                            symbol=event.symbol,
                            exit_price=event.price
                        )
                        logging.info(f"Trade closed: {event.symbol} at {event.price}")
            except Exception as e:
                logging.error(f"TradingEngine event error: {e}")
