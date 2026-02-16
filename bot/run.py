import json
from datetime import datetime, timedelta, timezone
from typing import Dict

from auth import FyersAuthManager
from fyers_adapter import FyersAdapter
from health import check_api_health
from utils import load_config, setup_logger


def _input_order_payload() -> Dict:
    print("Paste full order JSON payload according to Fyers docsv3 (single line):")
    raw = input("> ").strip()
    return json.loads(raw)


def main() -> None:
    config = load_config()
    logger = setup_logger("logs/bot.log")

    logger.info("CLI started", extra={"details": {"base_url": config.base_url}})

    health = check_api_health(config, logger)
    if not health.healthy:
        print(f"API health check failed ({health.status_code}): {health.message}")
        print("Aborting before OAuth/trading calls.")
        return

    auth = FyersAuthManager(config, logger)
    access_token = auth.get_valid_access_token()
    print("Authentication successful.")

    adapter = FyersAdapter(config, access_token, logger)

    menu = """
Select command:
1. Fetch LTP
2. Fetch History
3. Place Test Order
4. Show Positions
5. Show Funds
6. Show Orderbook
7. Exit
"""

    while True:
        print(menu)
        choice = input("Enter choice: ").strip()

        try:
            if choice == "1":
                symbol = input("Symbol (e.g. NSE:NIFTY50-INDEX): ").strip()
                data = adapter.get_ltp(symbol)
                print(json.dumps(data, indent=2))

            elif choice == "2":
                symbol = input("Symbol: ").strip()
                resolution = input("Resolution (e.g. 5): ").strip()
                now = datetime.now(timezone.utc)
                default_from = (now - timedelta(days=1)).strftime("%Y-%m-%d")
                default_to = now.strftime("%Y-%m-%d")
                range_from = input(f"From date YYYY-MM-DD [{default_from}]: ").strip() or default_from
                range_to = input(f"To date YYYY-MM-DD [{default_to}]: ").strip() or default_to
                data = adapter.get_history(symbol, resolution, range_from, range_to)
                print(json.dumps(data, indent=2))

            elif choice == "3":
                payload = _input_order_payload()
                data = adapter.place_order(payload)
                print(json.dumps(data, indent=2))

            elif choice == "4":
                data = adapter.get_positions()
                print(json.dumps(data, indent=2))

            elif choice == "5":
                data = adapter.get_funds()
                print(json.dumps(data, indent=2))

            elif choice == "6":
                data = adapter.get_orderbook()
                print(json.dumps(data, indent=2))

            elif choice == "7":
                print("Bye.")
                break

            else:
                print("Invalid choice.")

        except json.JSONDecodeError:
            print("Invalid JSON payload.")
        except Exception as exc:
            logger.error("CLI command failed", extra={"details": {"error": str(exc)}})
            print(f"Error: {exc}")


if __name__ == "__main__":
    main()
