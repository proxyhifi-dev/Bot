
import requests
import os
from dotenv import load_dotenv
from typing import Optional

load_dotenv()

TOKEN: Optional[str] = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID: Optional[str] = os.getenv("TELEGRAM_CHAT_ID")

def send_message(text: str) -> None:
    """
    Send a message to a Telegram chat using a bot token.

    Args:
        text (str): The message to send.
    """
    if not TOKEN or not CHAT_ID:
        print("[Notifier] Telegram token or chat ID not set.")
        return
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try:
        resp = requests.post(url, data={"chat_id": CHAT_ID, "text": text})
        if not resp.ok:
            print(f"[Notifier] Failed to send message: {resp.text}")
    except Exception as e:
        print(f"[Notifier] Exception: {e}")
