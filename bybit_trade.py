import asyncio
import websockets
import datetime
import time
import json
import hmac
import telegram
import os
from telegram.request import HTTPXRequest
from pybit.unified_trading import HTTP
from dotenv import load_dotenv

hold_amount = 0.0               # 보유한 개수
target_hold_amount = 0.001      # 구매할 개수 
buy_price = None                # 매수한 금액
target_take_profit_ratio = 0.1  # 1%
target_stop_loss_ratio = -0.01  # -1%
trade_ended = False             # 트레이딩 종료 유무 판단
last_notify_time = 0
# Bybit API 키 정보 (본인 정보 입력)
load_dotenv()

api_key = os.getenv("API_KEY")
api_secret = os.getenv("API_SECRET")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

session = HTTP(
    testnet=True,
    api_key=api_key,
    api_secret=api_secret
)

request = HTTPXRequest(read_timeout=10.0, connect_timeout=10.0)
telegram_bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN, request=request)

def send_auth():
    expires = int((time.time() + 10) * 1000)
    _val = f'GET/realtime{expires}'
    signature = hmac.new(
        api_secret.encode(),
        _val.encode(),
        digestmod='sha256'
    ).hexdigest()
    return json.dumps({
        "op": "auth",
        "args": [api_key, expires, signature]
    })

async def notify(text):
    try:
        await telegram_bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=text)
    except Exception as e:
        print(f"[Telegram Error] {e}")

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
    #포지션 정보 가져오기
    positions = session.get_positions(category="linear", symbol="BTCUSDT")
    pos = positions['result']['list'][0]
    # 실체결가
    base_price = float(pos['avgPrice'])  
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
    hold_amount = float(pos["size"])
    side = "LONG" if pos["side"] == "Buy" else "SHORT"
    await notify(
        f"{str(datetime.datetime.now())}\n"
        f"[[[[[[[포지션진입]]]]]]]\n"
        f"[진입가]:{base_price}\n"
        f"[TP]:{take_profit}\n"
        f"[SL]:{stop_loss}\n"
        f"[SIDE]:{side}\n"
        f"[수량]:{pos["size"]}\n"
        
    )
    print(f"[진입가]:{base_price}, [TP]:{take_profit}, [SL]:{stop_loss}")
    return hold_amount

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

async def bybit_private_ws():
        while True:
            try:
                async with websockets.connect("wss://stream-testnet.bybit.com/v5/private?max_active_time=10m") as ws_private:
                    print("✅ Private WebSocket 연결됨")
                    await ws_private.send(send_auth())  # () 붙여야 됨!
                    await ws_private.send(json.dumps({
                        "op": "subscribe",
                        "args": ["execution", "wallet"]
                    }))

                    while True:
                        data_rcv_strjson = await ws_private.recv()
                        rawdata = json.loads(data_rcv_strjson)
                        print("📥 [PRIVATE]", rawdata)
                        if "data" in rawdata and rawdata["topic"] == "execution":
                            exec_data = rawdata["data"][0]
                            if float(exec_data["closedSize"]) > 0:
                                symbol = exec_data["symbol"]
                                price = exec_data["execValue"]
                                side = exec_data["side"]
                                size = exec_data["closedSize"]
                                execPnl = exec_data["execPnl"]
                                side = "SHORT" if side == "Buy" else "LONG"
                                await notify(
                                    f"{str(datetime.datetime.now())}\n"
                                    f"[[[[[[{side}포지션청산]]]]]]\n"
                                    f"[{symbol}][체결금액]: {price} USDT\n"
                                    f"[체결수량]: {size}"
                                    f"[수익/손실]: {execPnl}"
                                )
                                print(f"[{symbol}][체결금액]: {price} USDT, {side}포지션 청산")
                        elif "data" in rawdata and rawdata["topic"] == "wallet":
                            exec_data = rawdata["data"][0]
                            totalEquity = exec_data["totalEquity"] #총 순자산
                            totalAvailableBalance = exec_data["totalAvailableBalance"] #주문 가능 잔액
                            walletBalance = exec_data["coin"][0]["walletBalance"]
                            await notify(
                                f"{str(datetime.datetime.now())}\n"
                                f"[[[[[[[[지갑]]]]]]]]\n"
                                f"[총 순자산]: {totalEquity}\n"
                                f"[주문가능잔액]: {totalAvailableBalance}\n"
                                f"[USDT개수]: {walletBalance}"
                            )
            except websockets.ConnectionClosed:
                print("❌ Private WebSocket 연결 끊김, 재연결 시도 중...")
                await asyncio.sleep(3)

async def bybit_ws_client():
    url = "wss://stream-testnet.bybit.com/v5/public/linear"
    global hold_amount
    global buy_price
    global trade_ended
    global mark_price
    while True:
        try:
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
                        
                        # 비트코인 현재가
                        if msg.get("topic") == "tickers.BTCUSDT":
                            mark_price = msg["data"].get("markPrice")
                        
                        if mark_price is not None:
                            #매매 조건
                            if trade_ended == False and hold_amount < target_hold_amount:
                                order = await place_order_with_tp_sl("Buy")
                                hold_amount = order
                                time.sleep(0.1)
                                
                            if trade_ended == False:
                                position = session.get_positions(
                                    category="linear",
                                    symbol="BTCUSDT"
                                )
                                if position["result"]["list"][0]["size"] == '0':
                                    print("+++++++++++++++포지션청산+++++++++++++++")
                                    hold_amount = 0.0
                                else :
                                    print(f'현재시간 : {current_time}, 현재가 : {mark_price}, 미실현수익 : {position["result"]["list"][0]["unrealisedPnl"]}')
                    except Exception as e_inner:
                        print(f"⚠️ 내부 처리 중 예외 발생: {e_inner}")
                        await notify(
                            f"{str(datetime.datetime.now())}⚠️\n"
                            f"내부 처리 중 예외 발생: {e_inner}")
                        break
                   
        except websockets.ConnectionClosed:
                print("❌ Public WebSocket 연결 끊김, 재연결 시도 중...")
                await notify(
                    f"{str(datetime.datetime.now())}\n"
                    f"❌ Public WebSocket 연결 끊김, 재연결 시도 중...")
                await asyncio.sleep(3)
                
async def main():
    await notify(f"{str(datetime.datetime.now())}\n"
                 f"+++++매매시작+++++")
    await asyncio.gather(
        bybit_private_ws(),
        bybit_ws_client()
    )

if __name__ == "__main__":
    asyncio.run(main())
