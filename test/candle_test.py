from pybit.unified_trading import HTTP
import pandas as pd
from urllib.parse import urlencode
import matplotlib.pyplot as plt
from datetime import datetime

api_key = "uobPGl5Ol3lBSqztB8"
api_secret = "SubtOb7Cwti2Bdan10gjNfkSe6ZZtbEhlcZL"

session = HTTP(
    testnet=True,
    api_key=api_key,
    api_secret=api_secret
)

ohlv = session.get_kline(
    category="linear",
    symbol="BTCUSDT",
    interval="D",
    limit=100
)

df = pd.DataFrame(ohlv["result"]["list"], columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'turnover'])
df['timestamp'] = pd.to_datetime(df['timestamp'].astype(float), unit='ms')
df = df.astype({'open': float, 'high': float, 'low': float, 'close': float})
df = df.sort_values(by="timestamp", ascending=True)
df.plot(x='timestamp', y='close', figsize=(10,10), grid=True)
print(df)

start_date = df.iloc[0]['timestamp'].strftime('%Y-%m-%d')
end_date = str(datetime.now().strftime('%Y-%m-%d'))
filename = f"C:/Users/ewide/Desktop/coin/log/BTC_day_candle_{start_date}_{end_date}.csv"
df.to_csv(filename)