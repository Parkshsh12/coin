import sys
import os
import pandas as pd
from pybit.unified_trading import HTTP
import matplotlib.pyplot as plt
from dotenv import load_dotenv
current_dir = os.path.dirname(os.path.abspath(__file__))
coin_dir = os.path.abspath(os.path.join(current_dir, ".."))
sys.path.append(coin_dir)
from util.trading_utils import get_ohlcv

load_dotenv()

api_key = os.getenv("API_KEY")
api_secret = os.getenv("API_SECRET")

session = HTTP(testnet=False, api_key=api_key, api_secret=api_secret)

# 데이터 로딩
df = get_ohlcv(session, symbol="BTCUSDT", interval="15", limit=1000)
# 이동평균선 계산
df["ma5"] = df["close"].rolling(window=5).mean()
df["ma10"] = df["close"].rolling(window=10).mean()
df["ma20"] = df["close"].rolling(window=20).mean()

capital = 10000  # 초기 자본
capital_log = [capital]
position = None
entry_price = 0
tp = sl = 0
wins = 0
losses = 0
trades = []

for i in range(20, len(df) - 1):
    price = df["close"].iloc[i]
    ma5 = df["ma5"].iloc[i]
    ma10 = df["ma10"].iloc[i]
    ma20 = df["ma20"].iloc[i]
    print(f"{price}, {ma5}, {ma10}, {ma20}")

    if position is None:
        if price > ma5 and price > ma10 and price > ma20:
            position = "long"
            entry_price = price
            tp = entry_price * 1.20
            sl = entry_price * 0.95
        elif price < ma5 and price < ma10 and price < ma20:
            position = "short"
            entry_price = price
            tp = entry_price * 0.80
            sl = entry_price * 1.05

    elif position == "long":
        high = df["high"].iloc[i + 1]
        low = df["low"].iloc[i + 1]
        if high >= tp or low <= sl:
            exit_price = tp if high >= tp else sl
            profit_pct = (exit_price - entry_price) / entry_price
            profit = capital * profit_pct
            capital += profit
            trades.append(profit)
            capital_log.append(capital)
            wins += 1 if profit > 0 else 0
            losses += 1 if profit < 0 else 0
            position = None

    elif position == "short":
        high = df["high"].iloc[i + 1]
        low = df["low"].iloc[i + 1]
        if low <= tp or high >= sl:
            exit_price = tp if low <= tp else sl
            profit_pct = (entry_price - exit_price) / entry_price
            profit = capital * profit_pct
            capital += profit
            trades.append(profit)
            capital_log.append(capital)
            wins += 1 if profit > 0 else 0
            losses += 1 if profit < 0 else 0
            position = None

# 출력
total_trades = wins + losses
win_rate = (wins / total_trades) * 100 if total_trades else 0
avg_profit = sum(trades) / total_trades if total_trades else 0

print(f"총 트레이드 수: {total_trades}")
print(f"승: {wins}, 패: {losses}")
print(f"승률: {win_rate:.2f}%")
print(f"최종 자본: ${capital:.2f}")
print(f"평균 수익: ${avg_profit:.2f}")
