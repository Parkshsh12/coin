import pandas as pd
import numpy as np

def get_ohlcv(session, symbol, interval, limit=1000):
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
    return df

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

def calc_swing_high_low(df, n=10):
    """Swing High / Low 포인트 판별"""
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
    return df

def check_stoch_divergence(df):
    """Stochastic 다이버전스 체크"""
    i = df.index[-1]
    lows = df.index[df['is_swing_low'] & (df.index <= i)]
    print(lows)
    if len(lows) >= 2:
        prev, curr = lows[-2], lows[-1]
        if df.at[curr, 'low'] < df.at[prev, 'low'] and df.at[curr, '%D'] > df.at[prev, '%D']:
            return "bull"

    highs = df.index[df['is_swing_high'] & (df.index <= i)]
    if len(highs) >= 2:
        prev, curr = highs[-2], highs[-1]
        if df.at[curr, 'high'] > df.at[prev, 'high'] and df.at[curr, '%D'] < df.at[prev, '%D']:
            return "bear"

    return None
