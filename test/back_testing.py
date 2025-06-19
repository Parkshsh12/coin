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
LIMIT       = 1500
RSI_PERIOD  = 14
SWING_N     = 5
LEVERAGE    = 25
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
    return df

df = get_ohlcv(session, SYMBOL, INTERVAL, LIMIT)

# 1) RSI 계산
delta      = df['close'].diff()
gain       = delta.clip(lower=0)
loss       = -delta.clip(upper=0)
avg_gain   = gain.ewm(alpha=1/RSI_PERIOD, adjust=False).mean()
avg_loss   = loss.ewm(alpha=1/RSI_PERIOD, adjust=False).mean()
df['RSI']  = 100 - (100 / (1 + avg_gain/avg_loss))

# 2) 스윙 로우
n = SWING_N
df['is_swing_low'] = (
    df['low']
      .rolling(window=2*n+1, center=True)
      .apply(lambda x: np.argmin(x)==n, raw=True)
      .fillna(False).astype(bool)
)

# 3) 다이버전스 체크
def check_regular_divergence(df, i):
    lows = df.index[df['is_swing_low'] & (df.index <= i)]
    if len(lows) < 2:
        return None
    prev, curr = lows[-2], lows[-1]
    p_prev, p_curr = df.at[prev,'low'], df.at[curr,'low']
    r_prev, r_curr = df.at[prev,'RSI'], df.at[curr,'RSI']
    if p_curr < p_prev and r_curr > r_prev:
        return "bull"
    if p_curr > p_prev and r_curr < r_prev:
        return "bear"
    return None

# 4) 백테스트 루프
capital      = 10000
capital_log  = [capital]
position     = None
entry_price  = 0
wins = losses = 0
trades = []

for i in range(50, len(df)-1):
    price = df.at[i,'close']
    time  = df.at[i,'timestamp']
    div   = check_regular_divergence(df, i)

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
    elif position=="long":
        exit_price     = df.at[i+1,'close']
        raw_pct        = (exit_price - entry_price) / entry_price * LEVERAGE
        net_pct        = raw_pct - 2*FEE_RATE
        profit         = capital * net_pct
        capital       += profit
        capital_log.append(capital)
        trades.append(profit)
        wins  += profit>0
        losses+= profit<0
        print(f"{'✅' if profit>0 else '❌'} LONG 종료 @{exit_price:.2f} | {df.at[i+1,'timestamp']}"
              f" | 수익률(수수료 후): {net_pct:.2%}, 수익: ${profit:.2f}")
        position = None

    elif position=="short":
        exit_price     = df.at[i+1,'close']
        raw_pct        = (entry_price - exit_price) / entry_price * LEVERAGE
        net_pct        = raw_pct - 2*FEE_RATE
        profit         = capital * net_pct
        capital       += profit
        capital_log.append(capital)
        trades.append(profit)
        wins  += profit>0
        losses+= profit<0
        print(f"{'✅' if profit>0 else '❌'} SHORT 종료 @{exit_price:.2f} | {df.at[i+1,'timestamp']}"
              f" | 수익률(수수료 후): {net_pct:.2%}, 수익: ${profit:.2f}")
        position = None

# — 최종 결과
total = wins + losses
print(f"\n📊 총 트레이드: {total}")
print(f"✅ 승: {wins}, ❌ 패: {losses}")
print(f"🏆 승률: {wins/total*100:.2f}%")
print(f"💰 최종 자본: ${capital:.2f}")
print(f"📈 평균 P&L: ${np.mean(trades):.2f}")

# — 차트
pd.Series(capital_log).plot(title="다이버전스 전략 누적 자본 (수수료 반영)")
plt.xlabel("트레이드 번호")
plt.ylabel("자본($)")
plt.grid()
plt.show()
