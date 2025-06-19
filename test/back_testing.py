import os
import pandas as pd
from pybit.unified_trading import HTTP
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()
api_key    = os.getenv("API_KEY")
api_secret = os.getenv("API_SECRET")
session    = HTTP(testnet=False, api_key=api_key, api_secret=api_secret)

def get_ohlcv(session, symbol, interval, limit=1500):
    data = session.get_kline(category="linear", symbol=symbol,
                             interval=interval, limit=limit)
    df = pd.DataFrame(data['result']['list'],
                      columns=['timestamp','open','high','low','close','volume','turnover'])
    df[['open','high','low','close']] = df[['open','high','low','close']].astype(float)
    df['timestamp'] = pd.to_datetime(df['timestamp'].astype(int), unit='ms')
    return df

df = get_ohlcv(session, "BTCUSDT", "15", limit=1500)

# ATR 계산
df['H-L']  = df['high'] - df['low']
df['H-PC'] = (df['high'] - df['close'].shift(1)).abs()
df['L-PC'] = (df['low']  - df['close'].shift(1)).abs()
df['TR']   = df[['H-L','H-PC','L-PC']].max(axis=1)
df['ATR']  = df['TR'].ewm(span=14, adjust=False).mean()

def detect_fvg(df):
    fvg_list = []
    for i in range(2, len(df)):
        h2, l2 = df['high'].iat[i-2], df['low'].iat[i-2]
        h1, l1 = df['high'].iat[i-1], df['low'].iat[i-1]
        h0, l0 = df['high'].iat[i  ], df['low'].iat[i  ]
        # 하락 FVG
        if l2 > h1 and l1 > h0:
            fvg_list.append({'start': i-1, 'top': l2, 'bot': h0, 'used': False})
        # 상승 FVG
        elif h2 < l1 and h1 < l0:
            fvg_list.append({'start': i-1, 'top': l0, 'bot': h2, 'used': False})
    return fvg_list

def detect_mss(df):
    mss = []
    for i in range(2, len(df)):
        if (df['low'].iat[i-2] > df['low'].iat[i-1] < df['low'].iat[i]
            and df['close'].iat[i] > df['high'].iat[i-2]):
            mss.append(i)
    return set(mss)

fvg_zones = detect_fvg(df)
mss_points = detect_mss(df)
print(f"▶ 검출된 FVG 개수: {len(fvg_zones)}")
print(f"▶ 검출된 MSS 개수: {len(mss_points)}")

# 백테스트 파라미터
capital      = 10000
leverage     = 10
tp_factor    = 2.0
sl_factor    = 1.0
position     = None
trades, wins, losses = [],0,0

for i in range(50, len(df)-1):
    price = df['close'].iat[i]
    atr   = df['ATR'].iat[i]
    time  = df['timestamp'].iat[i]
    # MSS 최근 3봉 내에 있나
    recent_mss = any(j in mss_points for j in range(i-3, i+1))
    # 미사용 FVG 중 ATR*1.5 이내 매칭
    match = None
    tol   = atr * 1.5
    for f in fvg_zones:
        if not f['used'] and f['start'] < i:
            if abs(price - f['top']) <= tol or abs(price - f['bot']) <= tol:
                match = f
                break

    print(f"[DEBUG] {time} | P:{price:.0f} | MSS:{recent_mss} | FVG:{match is not None}")

    # 진입
    if position is None and recent_mss and match:
        entry = price
        tp    = entry + atr*tp_factor
        sl    = entry - atr*sl_factor
        position = 'long'
        match['used'] = True
        print(f"▶ LONG IN @ {entry:.2f}")

    # 청산
    elif position=='long':
        nh, nl = df['high'].iat[i+1], df['low'].iat[i+1]
        nt     = df['timestamp'].iat[i+1]
        if nh>=tp or nl<=sl:
            exit_p = tp if nh>=tp else sl
            ret    = (exit_p-entry)/entry*leverage
            profit = capital*ret
            capital+= profit
            trades.append(profit)
            if profit>0: wins+=1
            else:       losses+=1
            print(f"{'✅' if profit>0 else '❌'} OUT @ {exit_p:.2f} | R:{ret:.2%}")
            position=None

# 결과
tot = wins+losses
print(f"\n=== 결과 ===")
print(f"트레이드 수: {tot}, 승:{wins}, 패:{losses}")
print(f"승률: {wins/tot*100 if tot else 0:.2f}%")
print(f"최종 자본: {capital:.2f}")
