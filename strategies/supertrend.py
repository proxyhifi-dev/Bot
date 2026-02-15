from engine.events import SignalEvent
import logging
from strategies.option_chain_logic import analyze_option_chain
from strategies.signal import generate_signal as pcr_signal

class SupertrendStrategy:
    def __init__(self):
        self.in_position = False

    def generate_signal(self, market_event, event_bus, option_chain=None):
        price = market_event.price
        try:
            # Option chain logic (if available)
            pcr = None
            if option_chain:
                oc_result = analyze_option_chain(option_chain)
                pcr = oc_result["PCR"]
                pcr_sig = pcr_signal(pcr)
                logging.info(f"Option Chain PCR: {pcr}, Signal: {pcr_sig}")
            else:
                pcr_sig = None

            # Combine Supertrend and PCR logic
            if price > 22000 and not self.in_position and (pcr_sig in [None, "BUY CE"]):
                logging.info(f"📈 BUY Signal at {price}")
                print(f"📈 BUY Signal at {price}")
                self.in_position = True
                event_bus.put(SignalEvent("NIFTY", "BUY", price))

            elif price < 21950 and self.in_position and (pcr_sig in [None, "BUY PE"]):
                logging.info(f"📉 EXIT Signal at {price}")
                print(f"📉 EXIT Signal at {price}")
                self.in_position = False
                event_bus.put(SignalEvent("NIFTY", "EXIT", price))
        except Exception as e:
            logging.error(f"SupertrendStrategy error: {e}")
