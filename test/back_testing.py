import sys
import os
import pandas as pd
from pybit.unified_trading import HTTP
import matplotlib.pyplot as plt

# 절대경로 추가
sys.path.append(r"C:\Users\ewide\Desktop\coin")

from util.trading_utils import get_ohlcv

api_key = "uobPGl5Ol3lBSqztB8"
api_secret = "SubtOb7Cwti2Bdan10gjNfkSe6ZZtbEhlcZL"

session = HTTP(testnet=True, api_key=api_key, api_secret=api_secret)

# 데이터 로딩
df = get_ohlcv(session, symbol="BTCUSDT", interval="5", limit=1000)
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

# 그래프 출력
pd.Series(capital_log).plot(title="📈 누적 자본 변화")
plt.xlabel("트레이드 번호")
plt.ylabel("자본($)")
plt.grid()
plt.show()