from pybit.unified_trading import HTTP
import time
import requests

api_key = "uobPGl5Ol3lBSqztB8"
api_secret = "SubtOb7Cwti2Bdan10gjNfkSe6ZZtbEhlcZL"

session = HTTP(
    testnet=True,
    api_key=api_key,
    api_secret=api_secret,
    recv_window=30000
)

# 잔고 확인
# 잔고 확인
balance = session.get_wallet_balance(accountType="UNIFIED", coin="USDT")
btc_info = balance['result']['list'][0]
print("잔고 확인:", balance)

server_time = requests.get("https://api-testnet.bybit.com/v5/market/time").json()
print("서버 시각:", server_time["time"])
print("내 시각:", int(time.time() * 1000))

# 시장가 매수 (예시: 0.001 BTC)
order = session.place_order(
    category="linear",
    symbol="BTCUSDT",
    side="Sell",
    orderType="Market",
    qty=0.001,
    timeInForce="GoodTillCancel"
)

print("주문 결과:", order)