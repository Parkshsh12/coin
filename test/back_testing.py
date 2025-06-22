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
INTERVAL    = "30"
LIMIT       = 1000
SWING_N     = 10
LEVERAGE    = 20
FEE_RATE    = 0.00075   # 0.075% per side

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

df = get_ohlcv(session, SYMBOL, INTERVAL, LIMIT)

def smma(series, period):
    """Wilder's Smoothing (SMMA) - TradingView와 일치"""
    smma = [np.nan] * len(series)
    first_valid = series.first_valid_index()
    if first_valid is None or first_valid + period > len(series):
        return pd.Series(smma, index=series.index)

    # 첫 SMMA 값은 단순 평균
    smma[first_valid + period - 1] = series.iloc[first_valid: first_valid + period].mean()

    # 이후부터는 SMMA 방식 적용
    for i in range(first_valid + period, len(series)):
        prev = smma[i - 1]
        smma[i] = (prev * (period - 1) + series.iloc[i]) / period

    return pd.Series(smma, index=series.index)

def calc_stochastic_smma(df, k_period=14, k_smooth=3, d_period=3):
    """TradingView 스타일: SMMA 기반 Slow Stochastic"""
    low_min = df['low'].rolling(window=k_period).min()

    high_max = df['high'].rolling(window=k_period).max()

    raw_k = 100 * (df['close'] - low_min) / (high_max - low_min+ 1e-9)
    smoothed_k = smma(raw_k, k_smooth)
    smoothed_d = smma(smoothed_k, d_period)

    df['%K'] = smoothed_k
    df['%D'] = smoothed_d
    return df

df = calc_stochastic_smma(df)

n = SWING_N
df['is_swing_low'] = (
    df['low'].rolling(window=2*n+1, center=True)
    .apply(lambda x: np.argmin(x) == n, raw=True)
    .fillna(False).astype(bool)
)
df['is_swing_high'] = (
    df['high'].rolling(window=2*n+1, center=True)
    .apply(lambda x: np.argmax(x) == n, raw=True)
    .fillna(False).astype(bool)
)

def check_stoch_divergence(df, i):
    lows = df.index[df['is_swing_low'] & (df.index <= i)]
    print(lows)
    if len(lows) >= 2:
        prev, curr = lows[-2], lows[-1]
        if df.at[curr, 'low'] < df.at[prev, 'low'] and df.at[curr, '%D'] > df.at[prev, '%D']:
            print(f'lows, {lows}')
            return "bull"

    highs = df.index[df['is_swing_high'] & (df.index <= i)]
    if len(highs) >= 2:
        prev, curr = highs[-2], highs[-1]
        if df.at[curr, 'high'] > df.at[prev, 'high'] and df.at[curr, '%D'] < df.at[prev, '%D']:
            print(f'highs, {highs}')
            return "bear"
    return None
# 4) 백테스트 루프
capital      = 10000
capital_log  = [capital]
position     = None
entry_price  = 0
wins = losses = 0
trades = []
for i in range(15, len(df)-1):
    price = df.at[i,'close']
    time  = df.at[i,'timestamp']
    div   = check_stoch_divergence(df, i)

    # — 진입
    if position is None and div=="bull":
        position    = "long"
        entry_price = price
        print(f"▶️ LONG 진입 @{entry_price:.2f} | {time}")

    elif position is None and div=="bear":
        position    = "short"
        entry_price = price
        print(f"▶️ SHORT 진입 @{entry_price:.2f} | {time}")

    # — 청산 (다음 봉 종가)
    elif position == "long":
        exit_price = df.at[i, 'close']
        raw_pct = (exit_price - entry_price) / entry_price * LEVERAGE
        net_pct = raw_pct - 2 * FEE_RATE

        if net_pct >= 0.10 or net_pct >= -0.03:
            profit = capital * net_pct
            capital += profit
            capital_log.append(capital)
            trades.append(profit)
            wins += profit > 0
            losses += profit < 0
            print(f"{'✅' if profit > 0 else '❌'} LONG 종료 @{exit_price:.2f} | {df.at[i,'timestamp']}"
                f" | 수익률(수수료 후): {net_pct:.2%}, 수익: ${profit:.2f}")
            position = None

    elif position == "short":
        exit_price = df.at[i, 'close']
        raw_pct = (entry_price - exit_price) / entry_price * LEVERAGE
        net_pct = raw_pct - 2 * FEE_RATE

        if net_pct >= 0.10 or net_pct >= -0.03:
            profit = capital * net_pct
            capital += profit
            capital_log.append(capital)
            trades.append(profit)
            wins += profit > 0
            losses += profit < 0
            print(f"{'✅' if profit > 0 else '❌'} SHORT 종료 @{exit_price:.2f} | {df.at[i+1,'timestamp']}"
                f" | 수익률(수수료 후): {net_pct:.2%}, 수익: ${profit:.2f}")
            position = None

# — 최종 결과
total = wins + losses
print(df)
if total > 0:
    print(f"\n📊 총 트레이드: {total}")
    print(f"✅ 승: {wins}, ❌ 패: {losses}")
    print(f"🏆 승률: {wins/total*100:.2f}%")
    print(f"💰 최종 자본: ${capital:.2f}")
    print(f"📈 평균 P&L: ${np.mean(trades):.2f}")
else:
    print("\n⚠️ 트레이드가 발생하지 않았습니다.")

pd.Series(capital_log).plot(title="📈 누적 자본 변화 (MA Crossover 양방향 전략)")
plt.xlabel("트레이드 번호")
plt.ylabel("자본($)")
plt.grid()
plt.show()
