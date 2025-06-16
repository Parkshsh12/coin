import asyncio
import websockets
import time
import hmac
import hashlib
import json
from pybit.unified_trading import HTTP

hold_xrp_amount = 0.0             # 보유한 XRP 개수
target_hold_amount = 0.001       # 구매할 XPP 개수 
xrp_buy_price = None              # 매수한 XRP 금액
target_take_profit_ratio = 0.1   # 1%
target_stop_loss_ratio = -0.01    # -1%
trade_ended = False               # 트레이딩 종료 유무 판단
# Bybit API 키 정보 (본인 정보 입력)
api_key = "uobPGl5Ol3lBSqztB8"
api_secret = "SubtOb7Cwti2Bdan10gjNfkSe6ZZtbEhlcZL"

session = HTTP(
    testnet=True,
    api_key=api_key,
    api_secret=api_secret
)

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
        symbol="BTCUSDT",
        side=order_side,
        orderType="Limit",
        price=str(entry_price),
        qty=str(target_hold_amount),
        takeProfit=str(take_profit),
        stopLoss=str(stop_loss),
        timeInForce="GTC",
    )
    print("진입 주문결과:", order)
    return order

def close_position(position_side):
    side = "Sell" if position_side == "Buy" else "Buy"
    print(f"시장가 {side}로 기존 포지션 청산 시도")
    order = session.place_order(
        category="linear",
        symbol="BTCUSDT",
        side=side,
        orderType="Market",
        qty=str(target_hold_amount),
        reduceOnly=True,
        timeInForce="GoodTillCancel"
    )
    print("청산 주문결과:", order)

async def bybit_ws_client():
    url = "wss://stream-testnet.bybit.com/v5/public/linear"
    global hold_xrp_amount
    global xrp_buy_price
    global trade_ended
    global mark_price
    
    async with websockets.connect(url) as ws:
        subscribe_msg = {
            "op": "subscribe",
            "args": ["tickers.BTCUSDT"]
        }
        await ws.send(json.dumps(subscribe_msg))
        while True:
            data = await ws.recv()
            msg = json.loads(data)
            if msg.get("topic") == "tickers.BTCUSDT":
                mark_price = msg["data"].get("markPrice")
                if mark_price is not None:
                    print("[PUBLIC]", mark_price)    
            balance = session.get_wallet_balance(accountType="UNIFIED", coin="USDT")
            print("잔고 확인:", balance)
            position = session.get_positions(
                category="linear",
                symbol="BTCUSDT"
            )
            print("포지션:", position)
async def main():
    await bybit_ws_client()

asyncio.run(main())