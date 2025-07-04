# config.py
import os
from dotenv import load_dotenv
from pybit.unified_trading import HTTP

load_dotenv()

api_key = os.getenv("API_KEY")
api_secret = os.getenv("API_SECRET")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

SYMBOL = "BTCUSDT"
INTERVAL = "5"
LIMIT = 1000
SWING_N = 10
position = None                 # 포지션 long or short
target_hold_amount = 0.001

session = HTTP(
    testnet=False,
    api_key=api_key,
    api_secret=api_secret
)
