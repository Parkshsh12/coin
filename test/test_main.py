from pybit.unified_trading import HTTP
import time
import requests
import pandas as pd

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

def get_ohlcv(session, symbol, interval, limit=100):
    ohlcv = session.get_kline(
        category="linear",
        symbol=symbol,
        interval=interval,
        limit=limit
    )
    print(ohlcv)
    df = pd.DataFrame(ohlcv['result']['list'],
                      columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'turnover'])
    df = df.astype({'open': float, 'high': float, 'low': float, 'close': float})
    df['timestamp'] = pd.to_datetime(df['timestamp'].astype(int), unit='ms')
    return df

def get_rsi(df, period=14):
    delta = df['close'].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    rs = avg_gain / (avg_loss + 1e-10)
    df['rsi'] = 100 - (100 / (1 + rs))
    return df

df = get_ohlcv(session, symbol="BTCUSDT", interval="1", limit=1000)
