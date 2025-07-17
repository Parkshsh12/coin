import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
from pybit.unified_trading import HTTP
from dotenv import load_dotenv

# .env 로드
load_dotenv()
session = HTTP(
    testnet=False,
    api_key=os.getenv("API_KEY"),
    api_secret=os.getenv("API_SECRET")
)

# OHLCV
def get_ohlcv(symbol="BTCUSDT", interval="15", limit=1000):
    result = session.get_kline(category="linear", symbol=symbol, interval=interval, limit=limit)
    df = pd.DataFrame(result["result"]["list"], columns=["timestamp", "open", "high", "low", "close", "volume", "turnover"])
    df = df.astype({"open": float, "high": float, "low": float, "close": float})
    df["timestamp"] = pd.to_datetime(df["timestamp"].astype(int), unit="ms")
    df.set_index("timestamp", inplace=True)
    return df

# ADX 계산
def calculate_adx(df, period=14):
    df['tr'] = np.maximum.reduce([
        df['high'] - df['low'],
        abs(df['high'] - df['close'].shift()),
        abs(df['low'] - df['close'].shift())
    ])
    df['+dm'] = np.where((df['high'] - df['high'].shift()) > (df['low'].shift() - df['low']), np.maximum(df['high'] - df['high'].shift(), 0), 0)
    df['-dm'] = np.where((df['low'].shift() - df['low']) > (df['high'] - df['high'].shift()), np.maximum(df['low'].shift() - df['low'], 0), 0)
    df['tr_smooth'] = df['tr'].rolling(window=period).mean()
    df['+di'] = 100 * (df['+dm'].rolling(window=period).mean() / df['tr_smooth'])
    df['-di'] = 100 * (df['-dm'].rolling(window=period).mean() / df['tr_smooth'])
    df['dx'] = 100 * abs(df['+di'] - df['-di']) / (df['+di'] + df['-di'])
    df['adx'] = df['dx'].rolling(window=period).mean()
    return df

# 전략 실행
def run_strategy(df):
    df['ema_20'] = df['close'].ewm(span=20).mean()
    df['ema_50'] = df['close'].ewm(span=50).mean()
    df = calculate_adx(df)

    capital = 100
    capital_log = [capital]
    trades = []
    position = {"long": 0, "short": 0}
    entry_price = {"long": 0, "short": 0}
    leverage = 10

    for i in range(60, len(df)):
        price = df['close'].iloc[i]
        adx = df['adx'].iloc[i]
        plus_di = df['+di'].iloc[i]
        minus_di = df['-di'].iloc[i]
        ema_20 = df['ema_20'].iloc[i]
        ema_50 = df['ema_50'].iloc[i]
        ema_20_prev = df['ema_20'].iloc[i - 1]
        ema_50_prev = df['ema_50'].iloc[i - 1]

        candle_bull = df['close'].iloc[i] > df['open'].iloc[i]
        candle_bear = df['close'].iloc[i] < df['open'].iloc[i]
        golden_cross = ema_20_prev < ema_50_prev and ema_20 > ema_50
        death_cross = ema_20_prev > ema_50_prev and ema_20 < ema_50

        # 진입
        if position["long"] == 0 and adx >= 25 and plus_di > minus_di and candle_bull and golden_cross:
            position["long"] = 1
            entry_price["long"] = price
        elif position["short"] == 0 and adx >= 25 and minus_di > plus_di and candle_bear and death_cross:
            position["short"] = 1
            entry_price["short"] = price

        # 롱 청산/물타기
        if position["long"]:
            pnl = (price - entry_price["long"]) / entry_price["long"] * leverage
            if pnl >= 0.1 or adx < 20 or minus_di > plus_di:
                capital += capital * pnl
                trades.append(capital * pnl)
                capital_log.append(capital)
                position["long"] = 0
            elif pnl < -0.05:
                entry_price["long"] = (entry_price["long"] + price) / 2

        # 숏 청산/물타기
        if position["short"]:
            pnl = (entry_price["short"] - price) / entry_price["short"] * leverage
            if pnl >= 0.1 or adx < 20 or plus_di > minus_di:
                capital += capital * pnl
                trades.append(capital * pnl)
                capital_log.append(capital)
                position["short"] = 0
            elif pnl < -0.05:
                entry_price["short"] = (entry_price["short"] + price) / 2

    return capital_log, trades

# 실행
df = get_ohlcv()
capital_log, trades = run_strategy(df)

# 시각화
plt.plot(capital_log)
plt.title("자본 변화 추이")
plt.xlabel("거래 수")
plt.ylabel("자본 ($)")
plt.grid()
plt.show()
