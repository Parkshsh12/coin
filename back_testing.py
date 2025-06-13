from pybit.unified_trading import HTTP
import pandas as pd
from trading_utils import get_ohlcv, get_rsi, get_bollinger

api_key = "uobPGl5Ol3lBSqztB8"
api_secret = "SubtOb7Cwti2Bdan10gjNfkSe6ZZtbEhlcZL"

session = HTTP(
    testnet=True,
    api_key=api_key,
    api_secret=api_secret
)

# OHLCV 과거 데이터 충분히 받아오기 (예: 1000개)

df = get_ohlcv(session, symbol="BTCUSDT", interval="15", limit=1000)
df = get_rsi(df, period=14)
df = get_bollinger(df, period=20, num_std=2)

trade_results = []
win = 0
lose = 0
total_profit = 0
position = None
entry_price = 0
tp = 0
sl = 0

for i in range(20, len(df)-1):
    close = df['close'].iloc[i]
    rsi = df['rsi'].iloc[i]
    bb_upper = df['bb_upper'].iloc[i]
    bb_lower = df['bb_lower'].iloc[i]

    # 롱 진입: 종가가 볼린저밴드 하단 이하 AND RSI 35 이하
    if close <= bb_lower and position is None:
        position = "Long"
        entry_price = close
        tp = entry_price * 1.01      # 익절 1%
        sl = entry_price * 0.999     # 손절 -0.5%
        print(f"[{df['timestamp'].iloc[i]}] 롱 진입! 진입가: {entry_price:.2f}, BB하단: {bb_lower:.2f}, RSI: {rsi:.2f}")

    # 숏 진입: 종가가 볼린저밴드 상단 이상 AND RSI 65 이상
    elif close >= bb_upper and position is None:
        position = "Short"
        entry_price = close
        tp = entry_price * 0.99      # 익절 -1%
        sl = entry_price * 1.001     # 손절 +0.5%
        print(f"[{df['timestamp'].iloc[i]}] 숏 진입! 진입가: {entry_price:.2f}, BB상단: {bb_upper:.2f}, RSI: {rsi:.2f}")

    # 롱 포지션 청산
    elif position == "Long":
        high = df['high'].iloc[i+1]
        low = df['low'].iloc[i+1]
        exit_price = None
        result = None
        if high >= tp:
            exit_price = tp
            result = "익절"
        elif low <= sl:
            exit_price = sl
            result = "손절"
        if exit_price is not None:
            profit = exit_price - entry_price
            trade_results.append(profit)
            total_profit += profit
            if profit > 0:
                win += 1
            else:
                lose += 1
            print(f"[{df['timestamp'].iloc[i+1]}] 롱 {result}! 청산가: {exit_price:.2f}, 수익: {profit:.2f}")
            position = None

    # 숏 포지션 청산
    elif position == "Short":
        high = df['high'].iloc[i+1]
        low = df['low'].iloc[i+1]
        exit_price = None
        result = None
        if low <= tp:
            exit_price = tp
            result = "익절"
        elif high >= sl:
            exit_price = sl
            result = "손절"
        if exit_price is not None:
            profit = entry_price - exit_price
            trade_results.append(profit)
            total_profit += profit
            if profit > 0:
                win += 1
            else:
                lose += 1
            print(f"[{df['timestamp'].iloc[i+1]}] 숏 {result}! 청산가: {exit_price:.2f}, 수익: {profit:.2f}")
            position = None

# 결과 출력
print(f"총 트레이드 횟수: {len(trade_results)}")
print(f"승률: {win/len(trade_results)*100 if trade_results else 0:.2f}%")
print(f"누적수익: {total_profit:.2f}")
print(f"평균 수익: {total_profit/len(trade_results) if trade_results else 0:.2f}")