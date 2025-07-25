# config.py
import os
from dotenv import load_dotenv
from pybit.unified_trading import HTTP

load_dotenv()

api_key = os.getenv("API_KEY")
api_secret = os.getenv("API_SECRET")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
## test : 모의매매 main : 실전매매
MODE = "test"
LEVERAGE = 10
SYMBOL = "BTCUSDT"
INTERVAL = "5"
LIMIT = 1000
SWING_N = 10
position = {"long": 0, "short": 0}
entry_price = {"long": 0.0, "short": 0.0}
qty = 0.001

session = HTTP(
    testnet=True,
    api_key=api_key,
    api_secret=api_secret
)
