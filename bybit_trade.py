import ssl
import os
import sys
sys.path.append(os.getcwd())
import certifi
import asyncio
import websockets
import datetime
import time
import json
import logging
import config_val
from core.auth import notify, send_auth
from core.trade_manager import open_position, update_position, close_position, calculate_pnl
import util.trading_utils
from collections import deque

log_date = datetime.datetime.now().strftime("%Y-%m-%d")
log_path = f"log/log_{log_date}.txt"
logging.basicConfig(filename=log_path, level=logging.INFO, encoding="utf-8")
logging.getLogger("httpx").setLevel(logging.WARNING)
ssl_context = ssl.create_default_context(cafile=certifi.where())

global_price = {"last_price": None}
ohlcv_cache = {"data": None, "last_updated": 0}
price_buffer = deque(maxlen=20)
ema_buffer = deque(maxlen=5)

# OHLCV 캐시 함수
def cached_ohlcv(session, symbol, interval, limit=200, ttl=10):
    now = time.time()
    print(1)
    if ohlcv_cache["data"] is None or now - ohlcv_cache["last_updated"] > ttl:
        print(11)
        df = util.trading_utils.get_ohlcv(session, symbol, interval, limit)
        print(111)
        ohlcv_cache["data"] = df
        ohlcv_cache["last_updated"] = now
    return ohlcv_cache["data"]

async def bybit_private_ws():
    while True:
        try:
            async with websockets.connect("wss://stream-testnet.bybit.com/v5/private", ssl=ssl_context) as ws_private:
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
                        print("🔁 private Ping 전송")
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
    url = "wss://stream-testnet.bybit.com/v5/public/linear"
    subscribe_msg = {
        "op": "subscribe",
        "args": ["tickers.BTCUSDT"]
    }

    while True:
        try:
            async with websockets.connect(url, ssl=ssl_context) as ws:
                await ws.send(json.dumps(subscribe_msg))
                logging.info("✅ WebSocket 연결 및 구독 완료")

                #private websocket 지속적으로 유지하기 위한 ping
                async def send_ping():
                    while True:
                        ping_msg = {
                            "op": "ping",
                            "req_id": "ping_002"
                        }
                        await ws.send(json.dumps(ping_msg))
                        print("🔁 public Ping 전송")
                        await asyncio.sleep(20)

                asyncio.create_task(send_ping())
                
                while True:
                    data = await ws.recv()
                    msg = json.loads(data)

                    last_price = msg.get("data", {}).get("lastPrice")
                    if last_price:
                        global_price["last_price"] = float(last_price)
                        print(last_price)
        except Exception as e:
            logging.warning(f"❌ WebSocket 예외: {e}")
            await asyncio.sleep(3)
                
# 전략 로직 실행 루프 (on_ticker 통합 버전)
async def strategy_loop():
    while True:
        price = global_price["last_price"]
        if price:
            try:
                price_buffer.append(price)
                
                ema_now = util.trading_utils.get_ema(price_buffer, span=5)
                ema_buffer.append(ema_now)

                if len(price_buffer) < 20 or len(ema_buffer) < 3:
                    await asyncio.sleep(1)
                    continue

                ema_prev = ema_buffer[-2]
                bb_upper, bb_lower = util.trading_utils.get_bbands(price_buffer)
                prev_price = price_buffer[-2]

                # 포지션/진입가 업데이트
                update_position()
                # 초기 진입
                if config_val.position["long"] == 0 and config_val.position["short"] == 0:
                    open_position("Buy", config_val.qty, 1)
                    open_position("Sell", config_val.qty, 2)
                    logging.info("🟢 초기 롱숏 동시 진입")
                    await asyncio.sleep(1)
                    continue

                # 수익률 계산
                long_pnl, short_pnl = calculate_pnl(price)

                # 추세 반전 조건
                trend_reversal = (
                    ema_now < ema_prev
                    or (prev_price > bb_upper and price < bb_upper)
                    or (prev_price < bb_lower and price > bb_lower)
                )

                if trend_reversal:
                    if long_pnl > 5:
                        close_position("long", 1)
                        open_position("Sell", config_val.qty * 3, 2)
                        logging.info("🔁 롱 익절 + 숏 물타기")
                    elif short_pnl > 5:
                        close_position("short", 2)
                        open_position("Buy", config_val.qty * 3, 1)
                        logging.info("🔁 숏 익절 + 롱 물타기")

                # 손절 조건
                if config_val.position["long"] >= config_val.qty * 3 and long_pnl < -5:
                    close_position("long", 1)
                    open_position("Sell", config_val.qty, 2)
                    logging.info("💥 롱 손절 + 숏 복구 진입")

                elif config_val.position["short"] >= config_val.qty * 3 and short_pnl < -5:
                    close_position("short", 2)
                    open_position("Buy", config_val.qty, 1)
                    logging.info("💥 숏 손절 + 롱 복구 진입")

                # 실시간 로그 출력
                logging.info(f"📊 Price: {price:.1f} | EMA: {ema_now:.1f} | BB↑: {bb_upper:.1f} ↓: {bb_lower:.1f} | 롱PnL: {long_pnl:.2f}% | 숏PnL: {short_pnl:.2f}%")

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
