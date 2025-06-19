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

df = get_ohlcv(session, "BTCUSDT", "15", limit=1500)

# 1) RSI 계산 (14)
delta = df['close'].diff()
gain = delta.clip(lower=0)
loss = -delta.clip(upper=0)
avg_gain = gain.ewm(alpha=1/14, adjust=False).mean()
avg_loss = loss.ewm(alpha=1/14, adjust=False).mean()
rs = avg_gain / avg_loss
df['RSI'] = 100 - (100 / (1 + rs))

# 2) 스윙 포인트 찾기 (low 기준 local minima)
#    앞뒤 n=5봉보다 낮은 저점만 스윙 low로 간주
n = 5
df['is_swing_low'] = (
    df['low']
    .rolling(window=2*n+1, center=True)
    .apply(lambda x: np.argmin(x)==n, raw=True)
    .fillna(0).astype(bool)
)

# 3) 다이버전스 감지 함수
def check_regular_divergence(df, i):
    """
    i 시점에서 직전 두 개의 스윙 low 인덱스를 가져와
    가격은 더 낮은 저점, RSI는 더 높은 저점이면 강세 다이버전스 리턴
    반대면 약세 다이버전스
    """
    lows = df.index[df['is_swing_low'] & (df.index <= i)]
    if len(lows) < 2:
        return None
    prev, curr = lows[-2], lows[-1]
    price_prev, price_curr = df.at[prev,'low'], df.at[curr,'low']
    rsi_prev,   rsi_curr   = df.at[prev,'RSI'], df.at[curr,'RSI']
    # 강세 레귤러: price_down & rsi_up
    if price_curr < price_prev and rsi_curr > rsi_prev:
        return "bull"
    # 약세 레귤러: price_up & rsi_down
    if price_curr > price_prev and rsi_curr < rsi_prev:
        return "bear"
    return None

# 4) 백테스트 루프에 다이버전스 로직 적용
capital = 10000
capital_log = [capital]
position = None
entry_price = tp = sl = 0
wins = losses = 0
trades = []
leverage = 25

for i in range(50, len(df)-1):
    price = df.at[i,'close']
    high  = df.at[i+1,'high']
    low   = df.at[i+1,'low']
    time  = df.at[i,'timestamp']
    div = check_regular_divergence(df, i)
    
    # 포지션 진입
    if position is None and div=="bull":
        position = "long"
        entry_price = price
        print(f"▶️ LONG 진입 @{entry_price:.2f} | {time}")
    elif position is None and div=="bear":
        position = "short"
        entry_price = price
        print(f"▶️ SHORT 진입 @{entry_price:.2f} | {time}")
    
    # 포지션 청산 (간단: 다음 봉 종가 청산)
    elif position=="long":
        exit_price = df.at[i+1,'close']
        profit_pct = (exit_price-entry_price)/entry_price * leverage
        profit = capital * profit_pct
        capital += profit; capital_log.append(capital)
        trades.append(profit)
        wins  += profit>0; losses += profit<0
        print(f"{'✅' if profit>0 else '❌'} LONG 종료 @{exit_price:.2f} | {df.at[i+1,'timestamp']} | 수익률: {profit_pct:.2%}, 수익: ${profit:.2f}")
        position = None
        
    elif position=="short":
        exit_price = df.at[i+1,'close']
        profit_pct = (entry_price-exit_price)/entry_price * leverage
        profit = capital * profit_pct
        capital += profit; capital_log.append(capital)
        trades.append(profit)
        wins  += profit>0; losses += profit<0
        print(f"{'✅' if profit>0 else '❌'} SHORT 종료 @{exit_price:.2f} | {df.at[i+1,'timestamp']} | 수익률: {profit_pct:.2%}, 수익: ${profit:.2f}")
        position = None

# 최종 통계
total = wins+losses
print(f"\n📊 총 트레이드: {total}")
print(f"✅ 승: {wins}, ❌ 패: {losses}")
print(f"🏆 승률: {wins/total*100:.2f}%")
print(f"💰 최종 자본: ${capital:.2f}")
print(f"📈 평균 P&L: ${np.mean(trades):.2f}")

# 결과 차트
pd.Series(capital_log).plot(title="다이버전스 전략 누적 자본")
plt.xlabel("트레이드 번호")
plt.ylabel("자본($)")
plt.grid()
plt.show()
