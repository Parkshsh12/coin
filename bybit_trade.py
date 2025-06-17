import asyncio
import websockets
import datetime
import time
import json
import telegram
from pybit.unified_trading import HTTP

hold_amount = 0.0               # 보유한 개수
target_hold_amount = 0.001      # 구매할 개수 
buy_price = None                # 매수한 금액
target_take_profit_ratio = 0.1  # 1%
target_stop_loss_ratio = -0.01  # -1%
trade_ended = False             # 트레이딩 종료 유무 판단
# Bybit API 키 정보 (본인 정보 입력)
api_key = "uobPGl5Ol3lBSqztB8"
api_secret = "SubtOb7Cwti2Bdan10gjNfkSe6ZZtbEhlcZL"

TELEGRAM_BOT_TOKEN = '8069042694:AAHjm7njb971ALxuFDg92Rm7arcJ0Bl5Mno'
TELEGRAM_CHAT_ID = '1946099028'

session = HTTP(
    testnet=True,
    api_key=api_key,
    api_secret=api_secret
)

telegram_bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)

async def notify(text):
    await telegram_bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=text)

async def place_order_with_tp_sl(order_side, tp_perc=0.011, sl_perc=0.005):
    order = session.place_order(
        category="linear",
        symbol="BTCUSDT",
        side=order_side,
        orderType="Market",
        qty=str(target_hold_amount),
        timeInForce="GTC",
    )
    print(f"진입 주문결과: {order["retMsg"]}, 주문번호: {order["result"]["orderId"]}")
    time.sleep(1)
    positions = session.get_positions(category="linear", symbol="BTCUSDT")
    pos = positions['result']['list'][0]
    base_price = float(pos['avgPrice'])  # 실체결가
    # 진짜 체결가로 TP/SL 재계산
    if order_side == "Buy":
        take_profit = round(base_price * (1 + tp_perc), 2)
        stop_loss = round(base_price * (1 - sl_perc), 2)
    else:
        take_profit = round(base_price * (1 - tp_perc), 2)
        stop_loss = round(base_price * (1 + sl_perc), 2)
    # TP/SL 주문 재설정 (modify 주문)
    session.set_trading_stop(
        category="linear",
        symbol="BTCUSDT",
        takeProfit=str(take_profit),
        stopLoss=str(stop_loss)
    )
    await notify(f"[진입가]:{base_price}, [TP]:{take_profit}, [SL]:{stop_loss}")
    print(f"[진입가]:{base_price}, [TP]:{take_profit}, [SL]:{stop_loss}")
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
    return order

async def bybit_ws_client():
    url = "wss://stream-testnet.bybit.com/v5/public/linear"
    global hold_amount
    global buy_price
    global trade_ended
    global mark_price
    
    async with websockets.connect(url, ping_interval=None) as ws:
        subscribe_msg = {
            "op": "subscribe",
            "args": ["tickers.BTCUSDT"]
        }
        await ws.send(json.dumps(subscribe_msg))
        while True:
            try:
                data = await ws.recv()
                msg = json.loads(data)
                if 'ts' in msg:
                    current_time = datetime.datetime.fromtimestamp(msg['ts'] / 1000)
                else:
                    print("ts 값이 없습니다:", msg)
                
                # 비트코인 현재가
                if msg.get("topic") == "tickers.BTCUSDT":
                    mark_price = msg["data"].get("markPrice")
                
                if mark_price is not None:
                    if trade_ended == False and hold_amount < target_hold_amount:
                        order = await place_order_with_tp_sl("Sell")
                        position = session.get_positions(
                            category="linear",
                            symbol="BTCUSDT"
                        )
                        buy_price = float(position["result"]["list"][0]["avgPrice"])
                        hold_amount = float(position["result"]["list"][0]["size"])
                        await notify(f"[체결가]: {buy_price}, [포지션]: {position["result"]["list"][0]["side"]}, [수량]: {position["result"]["list"][0]["size"]}")
                        print(f"[SIDE]: {position["result"]["list"][0]["side"]} [QTY]: {position["result"]["list"][0]["size"]}")
                        time.sleep(0.1)
                        
                    if trade_ended == False:
                        position = session.get_positions(
                            category="linear",
                            symbol="BTCUSDT"
                        )
                        if position["result"]["list"][0]["size"] == '0':
                            await notify("+++++++매도완료+++++++")
                            print("++++++++++++++++++++매도완료+++++++++++++++")
                            hold_amount = 0.0
                        else :
                            print(f'현재시간 : {current_time}, 현재가 : {mark_price}, 미실현수익 : {position["result"]["list"][0]["unrealisedPnl"]}')
            except Exception as excep:
                print(excep)
                
                if ws.closed:
                    ws = await websockets.connect(url, ping_interval=None)
                    
                    subscribe_msg = {
                        "op": "subscribe",
                        "args": ["tickers.BTCUSDT"]
                    }
                    await ws.send(json.dumps(subscribe_msg))
            
async def main():
    await notify(f"{str(datetime.datetime.now())}, '매매시작'")
    await bybit_ws_client()

if __name__ == "__main__":
    asyncio.run(main())
