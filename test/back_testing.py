# -*- coding: utf-8 -*-
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pybit.unified_trading import HTTP
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()
session = HTTP(
    testnet=False,
    api_key=os.getenv("API_KEY"),
    api_secret=os.getenv("API_SECRET")
)

# 전략 로직: 롱숏 동시 진입, 수익방향 청산 후 손실방향 물타기
def dual_hedge_recovery_strategy(df, leverage=20, fee=0.00075):
    capital = 100
    capital_log = [capital]
    saved_profit = 0
    position = {"long": 0, "short": 0}
    entry_price = {"long": 0, "short": 0}
    trades = []

    def open_position(pos, qty, price):
        if position[pos] == 0:
            entry_price[pos] = price
        else:
            entry_price[pos] = (entry_price[pos] * position[pos] + price * qty) / (position[pos] + qty)
        position[pos] += qty

    def close_position(pos, price):
        nonlocal capital, saved_profit
        if position[pos] == 0:
            return
        pnl = (price - entry_price[pos]) / entry_price[pos] * leverage
        if pos == "short":
            pnl *= -1
        net_profit = capital * pnl - capital * 2 * fee
        capital += net_profit
        saved_profit += net_profit
        trades.append(net_profit)
        capital_log.append(capital)
        position[pos] = 0
        entry_price[pos] = 0

    for i in range(30, len(df)):
        price = df.at[i, 'close']
        prev_price = df.at[i-1, 'close']
        ema_now = df.at[i-1, 'ema']
        ema_prev = df.at[i-2, 'ema']
        bb_upper = df.at[i-1, 'bb_upper']
        bb_lower = df.at[i-1, 'bb_lower']

        # 초기 1:1 진입
        if position["long"] == 0 and position["short"] == 0:
            open_position("long", 1, price)
            open_position("short", 1, price)
            continue

        # 추세 꺾임 판단
        trend_reversal = (ema_now < ema_prev) or (prev_price > bb_upper and price < bb_upper) or (prev_price < bb_lower and price > bb_lower)
        long_pnl = 0
        short_pnl = 0
        if position["long"] > 0 and entry_price["long"] != 0:
            long_pnl = (price - entry_price["long"]) / entry_price["long"] * leverage
        if position["short"] > 0 and entry_price["short"] != 0:
            short_pnl = (entry_price["short"] - price) / entry_price["short"] * leverage

        # 수익 포지션 정리 + 손실 포지션 물타기
        if trend_reversal:
            if long_pnl > 0:
                close_position("long", price)
                open_position("short", 3, price)
            elif short_pnl > 0:
                close_position("short", price)
                open_position("long", 3, price)

        # 추세 실패 시 손절 + 반대포지션 복구
        if position["long"] >= 3 and long_pnl < -0.05:
            close_position("long", price)
            open_position("short", 1, price)
        elif position["short"] >= 3 and short_pnl < -0.05:
            close_position("short", price)
            open_position("long", 1, price)

    return capital_log, trades

def add_indicators(df, ema_period=5, bb_period=20, bb_std=2):
    df["ema"] = df["close"].ewm(span=ema_period, adjust=False).mean()
    df["bb_mid"] = df["close"].rolling(bb_period).mean()
    df["bb_std"] = df["close"].rolling(bb_period).std()
    df["bb_upper"] = df["bb_mid"] + bb_std * df["bb_std"]
    df["bb_lower"] = df["bb_mid"] - bb_std * df["bb_std"]
    return df


def get_ohlcv(session, symbol, interval, limit):
    """Bybit에서 OHLCV 캔들 데이터 불러오기"""
    resp = session.get_kline(
        category="linear",
        symbol=symbol,
        interval=interval,
        limit=limit
    )
    df = pd.DataFrame(resp['result']['list'],
                      columns=['timestamp','open','high','low','close','volume','turnover'])
    df = df.astype({'open':float, 'high':float, 'low':float, 'close':float})
    df['timestamp'] = pd.to_datetime(df['timestamp'].astype(int), unit='ms')
    df = df.sort_values('timestamp').reset_index(drop=True)
    return df

df = get_ohlcv(session, symbol="BTCUSDT", interval="30", limit=1000)
df = add_indicators(df)

# 전략 실행
capital_log, trades = dual_hedge_recovery_strategy(df)

# 결과 출력
print(f"총 트레이드 수: {len(trades)}")
print(f"최종 자본: ${capital_log[-1]:.2f}")
print(f"평균 수익: ${np.mean(trades):.2f}")
pd.Series(capital_log).plot(title="누적 자본 변화")
plt.xlabel("트레이드 번호")
plt.ylabel("자본($)")
plt.grid()
plt.show()