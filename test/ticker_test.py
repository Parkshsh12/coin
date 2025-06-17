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

res = session.get_instruments_info(
    category="linear"
)

symbols = [item['symbol'] for item in res['result']['list']]
print(f"총 {len(symbols)}개 심볼:\n", symbols)

# DataFrame으로 정리
df = pd.DataFrame(res['result']['list'], columns=['symbol', 'baseCoin', 'quoteCoin', 'status'])
print(df)

df.to_csv("C:/Users/ewide/Desktop/coin/log/symbol_list.csv")