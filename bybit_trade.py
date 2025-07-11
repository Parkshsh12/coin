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
from core.trade_manager import place_order_with_tp_sl
import util.trading_utils

log_date = datetime.datetime.now().strftime("%Y-%m-%d")
log_path = f"log/log_{log_date}.txt"
logging.basicConfig(filename=log_path, level=logging.INFO, encoding="utf-8")
logging.getLogger("httpx").setLevel(logging.WARNING)
ssl_context = ssl.create_default_context(cafile=certifi.where())

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
    while True:
        try:
            async with websockets.connect(url, ssl=ssl_context) as ws:
                subscribe_msg = {
                    "op": "subscribe",
                    "args": ["tickers.BTCUSDT"]
                }
                await ws.send(json.dumps(subscribe_msg))
                while True:
                    try:
                        data = await ws.recv()
                        msg = json.loads(data)
                        # 비트코인 현재가
                        if msg.get("topic") == "tickers.BTCUSDT":
                            mark_price = msg["data"].get("markPrice")
                        
                        if mark_price is not None:
                            #매매 조건

                            df = util.trading_utils.get_ohlcv(config_val.session, config_val.SYMBOL, config_val.INTERVAL, config_val.LIMIT)
                            df = util.trading_utils.ma_line(df)
                            
                    except Exception as e_inner:
                        logging.info(f"⚠️ 내부 처리 중 예외 발생: {e_inner}")
                        await notify(
                            f"{str(datetime.datetime.now())}⚠️\n"
                            f"내부 처리 중 예외 발생: {e_inner}")
                        break
                   
        except (websockets.ConnectionClosed, websockets.WebSocketException) as e:
                logging.info(f"❌ public WebSocket 연결 끊김 또는 예외 발생: {e}. 3초 후 재시도...")
                await notify(f"❌ public WebSocket 연결 끊김 또는 예외 발생: {e}. 3초 후 재시도...")
                await asyncio.sleep(3)

        except Exception as e:
            logging.info(f"⚠️ 예상치 못한 예외: {e}. 5초 후 재시도...")
            await notify(f"⚠️ public WebSocket 예상치 못한 예외: {e}. 5초 후 재시도...")
            await asyncio.sleep(5)
                
async def main():
    logging.info("🚀 자동매매 시작")
    await notify(f"{str(datetime.datetime.now())}\n"
                 f"+++++매매시작+++++")
    await asyncio.gather(
        bybit_private_ws(),
        bybit_ws_client()
    )

if __name__ == "__main__":
    asyncio.run(main())
