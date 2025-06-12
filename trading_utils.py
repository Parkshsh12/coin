# trading_utils.py
import pandas as pd

def get_ohlcv(session, symbol, interval, limit=100):
    ohlcv = session.get_kline(
        category="linear",
        symbol=symbol,
        interval=interval,
        limit=limit
    )
    df = pd.DataFrame(ohlcv['result']['list'],
                      columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'turnover'])
    df = df.astype({'open': float, 'high': float, 'low': float, 'close': float})
    df['timestamp'] = pd.to_datetime(df['timestamp'].astype(int), unit='ms')
    return df

def get_rsi(df, period=14):
    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    rs = avg_gain / (avg_loss + 1e-10)
    df['rsi'] = 100 - (100 / (1 + rs))
    return df

def get_bollinger(df, period=20, num_std=2):
    df['bb_ma'] = df['close'].rolling(window=period).mean()
    df['bb_std'] = df['close'].rolling(window=period).std()
    df['bb_upper'] = df['bb_ma'] + (df['bb_std'] * num_std)
    df['bb_lower'] = df['bb_ma'] - (df['bb_std'] * num_std)
    return df