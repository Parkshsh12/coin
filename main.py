import time
import pandas as pd
from pybit.unified_trading import HTTP

from trading_utils import get_rsi, get_bollinger, get_ohlcv

symbol = "BTCUSDT"
interval = "1"
api_key = "uobPGl5Ol3lBSqztB8"
api_secret = "SubtOb7Cwti2Bdan10gjNfkSe6ZZtbEhlcZL"

session = HTTP(
    testnet=True,
    api_key=api_key,
    api_secret=api_secret
)

# 잔고 확인
balance = session.get_wallet_balance(accountType="UNIFIED", coin="USDT")
btc_info = balance['result']['list'][0]
print("잔고 확인:", balance)

usdt_balance = float(balance['result']['list'][0]['totalEquity'])   # 또는 availableBalance

# 100% 풀베팅
trade_amount = usdt_balance * 1.0   # 전액 사용



def get_position_info():
    positions = session.get_positions(category="linear", symbol=symbol)
    for pos in positions['result']['list']:
        if float(pos['size']) > 0:
            return pos
    return None

def close_position(position_side):
    side = "Sell" if position_side == "Buy" else "Buy"
    print(f"시장가 {side}로 기존 포지션 청산 시도")
    order = session.place_order(
        category="linear",
        symbol=symbol,
        side=side,
        orderType="Market",
        qty=qty,
        reduceOnly=True,
        timeInForce="GoodTillCancel"
    )
    print("청산 주문결과:", order)

def place_order_with_tp_sl(order_side, entry_price, tp_perc=0.01, sl_perc=0.005):
    if order_side == "Buy":
        take_profit = round(entry_price * (1 + tp_perc), 2)
        stop_loss = round(entry_price * (1 - sl_perc), 2)
    else:
        take_profit = round(entry_price * (1 - tp_perc), 2)
        stop_loss = round(entry_price * (1 + sl_perc), 2)
    print(f"{order_side} 주문: 진입가={entry_price}, TP={take_profit}, SL={stop_loss}")
    order = session.place_order(
        category="linear",
        symbol=symbol,
        side=order_side,
        orderType="Market",
        qty=str(qty),
        takeProfit=take_profit,
        stopLoss=stop_loss,
        timeInForce="GoodTillCancel"
    )
    print("진입 주문결과:", order)
    return order

# 자동매매 시작
while True:
    try:
        df = get_ohlcv(session, symbol, interval, limit=1000)
        df = get_rsi(df)
        df = get_bollinger(df)
        
        # 최신가로 주문 수량 계산
        current_price = float(df['close'].iloc[0])
        qty = round(trade_amount / current_price, 3)  # 소수점 3자리(최소수량 확인!)

        close = df['close'].iloc[0]
        rsi = df['rsi'].iloc[0]
        bb_upper = df['bb_upper'].iloc[0]
        bb_lower = df['bb_lower'].iloc[0]

        position_info = get_position_info()
        position_side = position_info['side'] if position_info else None
        print(df)
        print(f"\n[{df['timestamp'].iloc[0]}] 현재가: {close:.2f}, RSI: {rsi:.2f}, BB상단: {bb_upper:.2f}, BB하단: {bb_lower:.2f}, 포지션: {position_side}")

        # 롱 진입
        if (position_side is None or position_side == "Sell") and close <= bb_lower and rsi <= 35:
            if position_side == "Sell":
                close_position("Sell")
                time.sleep(10)
            order = place_order_with_tp_sl("Buy", close, tp_perc=0.01, sl_perc=0.005)

        # 숏 진입
        elif (position_side is None or position_side == "Buy") and close >= bb_upper and rsi >= 65:
            if position_side == "Buy":
                close_position("Buy")
                time.sleep(1)
            order = place_order_with_tp_sl("Sell", close, tp_perc=0.01, sl_perc=0.005)

        print("총 평가금액:", btc_info['totalEquity'])
        ticker = session.get_tickers(category="linear", symbol="BTCUSDT")
        print("비트코인 현재가:", ticker['result']['list'][0]['lastPrice'])

    except Exception as e:
        print("에러:", e)

    time.sleep(5)