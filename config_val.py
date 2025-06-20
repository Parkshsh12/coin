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
INTERVAL = "30"
LIMIT = 1000
SWING_N = 10
LEVERAGE = 20
FEE_RATE = 0.00075
hold_amount = 0.0               # 보유한 개수
target_hold_amount = 0.001      # 구매할 개수 
trade_ended = False             # 트레이딩 종료 유무 판단

session = HTTP(
    testnet=False,
    api_key=api_key,
    api_secret=api_secret
)
