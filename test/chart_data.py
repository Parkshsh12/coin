from pybit.unified_trading import HTTP
import pandas as pd
import os

session = HTTP(
    testnet=False,
    api_key=os.getenv("API_KEY"),
    api_secret=os.getenv("API_SECRET")
)
klines = session.get_kline(category="linear", symbol="BTCUSDT", interval="60", limit=1000)
df = pd.DataFrame(klines["result"]["list"])
df.columns = ["timestamp", "open", "high", "low", "close", "volume", "turnover"]
df['timestamp'] = pd.to_datetime(df['timestamp'].astype(int), unit='ms')
df.set_index("timestamp", inplace=True)
df.to_csv("BTCUSDT_1h.csv")