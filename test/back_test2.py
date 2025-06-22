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

# 백테스트 파라미터
SYMBOL      = "BTCUSDT"
INTERVAL    = "5"
LIMIT       = 1000
SWING_N     = 10
LEVERAGE    = 20
FEE_RATE    = 0.00075   # 0.075% per side
STOP_LOSS_PCT = -0.05   # 손절 기준

def get_ohlcv(session, symbol, interval, limit=1000):
    resp = session.get_kline(
        category="linear",
        symbol=symbol,
        interval=interval,
        limit=limit
    )
    df = pd.DataFrame(resp['result']['list'],
                      columns=['timestamp','open','high','low','close','volume','turnover'])
    df = df.astype({'open':float,'high':float,'low':float,'close':float})
    df['timestamp'] = pd.to_datetime(df['timestamp'].astype(int), unit='ms')
    df = df.sort_values('timestamp').reset_index(drop=True)
    return df

def run_strategy(df):
    df['MA50'] = df['close'].rolling(window=50).mean()
    df['MA200'] = df['close'].rolling(window=200).mean()
    return df

df = get_ohlcv(session, SYMBOL, INTERVAL, LIMIT)
df = run_strategy(df)

# 백테스트 루프
capital      = 10000
capital_log  = [capital]
position     = None
entry_price  = 0
trades = []

for i in range(200, len(df)):
    price = df.at[i, 'close']
    ma50 = df.at[i, 'MA50']
    ma200 = df.at[i, 'MA200']
    prev_ma50 = df.at[i-1, 'MA50']
    prev_ma200 = df.at[i-1, 'MA200']

    # 진입 조건
    if position is None:
        if prev_ma50 < prev_ma200 and ma50 > ma200:
            position = "long"
            entry_price = price
            print(f"▶️ LONG 진입 @{price:.2f} | {df.at[i, 'timestamp']}")
        elif prev_ma50 > prev_ma200 and ma50 < ma200:
            position = "short"
            entry_price = price
            print(f"▶️ SHORT 진입 @{price:.2f} | {df.at[i, 'timestamp']}")

    # 청산 조건: 50일선 닿거나 -5% 손실
    elif position == "long":
        raw_pnl = (price - entry_price) / entry_price
        if price <= ma50 or raw_pnl <= STOP_LOSS_PCT:
            pnl = raw_pnl * LEVERAGE - 2 * FEE_RATE
            profit = capital * pnl
            capital += profit
            trades.append(profit)
            capital_log.append(capital)
            print(f"{'✅' if profit > 0 else '❌'} LONG 종료 @{price:.2f} | {df.at[i, 'timestamp']} | 수익: ${profit:.2f}")
            position = None

    elif position == "short":
        raw_pnl = (entry_price - price) / entry_price
        if price >= ma50 or raw_pnl >= STOP_LOSS_PCT:
            pnl = raw_pnl * LEVERAGE - 2 * FEE_RATE
            profit = capital * pnl
            capital += profit
            trades.append(profit)
            capital_log.append(capital)
            print(f"{'✅' if profit > 0 else '❌'} SHORT 종료 @{price:.2f} | {df.at[i, 'timestamp']} | 수익: ${profit:.2f}")
            position = None

# 최종 결과 출력
print(f"\n📊 총 트레이드: {len(trades)}")
print(f"💰 최종 자본: ${capital:.2f}")
print(f"📈 평균 수익: ${np.mean(trades):.2f}" if trades else "트레이드 없음")

pd.Series(capital_log).plot(title="📈 누적 자본 변화 (MA Crossover + SL 전략)")
plt.xlabel("트레이드 번호")
plt.ylabel("자본($)")
plt.grid()
plt.show()
