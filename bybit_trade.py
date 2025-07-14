import ssl
import certifi
import asyncio
import websockets
import datetime
import time
import json
import logging
import config_val
from core.auth import notify, send_auth
from core.trade_manager import open_position
import util.trading_utils
from collections import deque

log_date = datetime.datetime.now().strftime("%Y-%m-%d")
log_path = f"log/log_{log_date}.txt"
logging.basicConfig(filename=log_path, level=logging.INFO, encoding="utf-8")
logging.getLogger("httpx").setLevel(logging.WARNING)
ssl_context = ssl.create_default_context(cafile=certifi.where())

global_price = {"mark_price": None}
ohlcv_cache = {"data": None, "last_updated": 0}
price_buffer = deque(maxlen=20)
ema_buffer = deque(maxlen=5)

# OHLCV 캐시 함수
def cached_ohlcv(session, symbol, interval, limit=200, ttl=10):
    now = time.time()
    if ohlcv_cache["data"] is None or now - ohlcv_cache["last_updated"] > ttl:
        df = util.trading_utils.get_ohlcv(session, symbol, interval, limit)
        df = util.trading_utils.ma_line(df)
        ohlcv_cache["data"] = df
        ohlcv_cache["last_updated"] = now
    return ohlcv_cache["data"]

async def bybit_private_ws():
    while True:
        try:
            async with websockets.connect("wss://stream.bybit.com/v5/private", ssl=ssl_context) as ws_private:
                logging.info("✅ Private WebSocket 연결됨")
                await ws_private.send(send_auth())  # () 붙여야 됨!
                await ws_private.send(json.dumps({
                    "op": "subscribe",
                    "args": ["execution", "wallet"]
                }))

                #private websocket 지속적으로 유지하기 위한 ping
                async def send_ping():
                    while True:
                        ping_msg = {
                            "op": "ping",
                            "req_id": "ping_001"
                        }
                        await ws_private.send(json.dumps(ping_msg))
                        print("🔁 Ping 전송")
                        await asyncio.sleep(20)

                asyncio.create_task(send_ping())
            
                while True:
                    data_rcv_strjson = await ws_private.recv()
                    rawdata = json.loads(data_rcv_strjson)
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
                                f"[체결수량]: {size}\n"
                                f"[수익/손실]: {execPnl}"
                            )
                            logging.info(f"{str(datetime.datetime.now())}\n"
                                f"[[[[[[{side}포지션청산]]]]]]\n"
                                f"[{symbol}][체결금액]: {price} USDT\n"
                                f"[체결수량]: {size}\n"
                                f"[수익/손실]: {execPnl}")
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
                        )
                        logging.info( f"{str(datetime.datetime.now())}\n"
                            f"[[[[[[[[지갑]]]]]]]]\n"
                            f"[총 순자산]: {totalEquity}\n"
                            f"[주문가능잔액]: {totalAvailableBalance}\n")
        except (websockets.ConnectionClosed, websockets.WebSocketException) as e:
            logging.info(f"❌ private WebSocket 연결 끊김 또는 예외 발생: {e}. 3초 후 재시도...")
            await notify(f"❌ private WebSocket 연결 끊김 또는 예외 발생: {e}. 3초 후 재시도...")
            await asyncio.sleep(3)

        except Exception as e:
            logging.info(f"⚠️ 예상치 못한 예외: {e}. 5초 후 재시도...")
            await notify(f"⚠️ private WebSocket 예상치 못한 예외: {e}. 5초 후 재시도...")
            await asyncio.sleep(5)

async def bybit_ws_client():
    url = "wss://stream.bybit.com/v5/public/linear"
    subscribe_msg = {
        "op": "subscribe",
        "args": ["tickers.BTCUSDT"]
    }

    while True:
        try:
            async with websockets.connect(url, ssl=ssl_context) as ws:
                await ws.send(json.dumps(subscribe_msg))
                logging.info("✅ WebSocket 연결 및 구독 완료")

                while True:
                    data = await ws.recv()
                    msg = json.loads(data)

                    mark_price = msg.get("data", {}).get("markPrice")
                    if mark_price:
                        global_price["mark_price"] = float(mark_price)

        except Exception as e:
            logging.warning(f"❌ WebSocket 예외: {e}")
            await asyncio.sleep(3)
                
# ✅ 전략 로직 실행 루프
async def strategy_loop():
    while True:
        price = global_price["mark_price"]
        if price:
            try:
                df = cached_ohlcv(config_val.session, config_val.SYMBOL, config_val.INTERVAL, config_val.LIMIT)
                
                # 전략 실행 조건 예시
                ema_now = df['ema'].iloc[-1]
                ema_prev = df['ema'].iloc[-2]
                bb_upper = df['bb_upper'].iloc[-1]
                bb_lower = df['bb_lower'].iloc[-1]
                prev_close = df['close'].iloc[-2]

                # 전략 조건
                trend_reversal = (
                    ema_now < ema_prev
                    or (prev_close > bb_upper and price < bb_upper)
                    or (prev_close < bb_lower and price > bb_lower)
                )

                if trend_reversal:
                    logging.info("📉 추세 반전 감지!")
                    # 여기에 진입/청산 로직 호출
                    # place_order(), close_position() 등

            except Exception as e:
                logging.error(f"❗ 전략 실행 중 오류: {e}")
                await notify(f"❗ 전략 실행 중 오류: {e}")

        await asyncio.sleep(1)
        
async def main():
    logging.info("🚀 자동매매 시작")
    await notify(f"{str(datetime.datetime.now())}\n"
                 f"+++++매매시작+++++")
    await asyncio.gather(
        bybit_private_ws(),
        bybit_ws_client(),
        strategy_loop()
    )

if __name__ == "__main__":
    asyncio.run(main())
