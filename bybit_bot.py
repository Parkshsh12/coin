# bybit_bot.py
import asyncio
import datetime
import random  # 예시용. 실제로는 bybit API 사용
from asyncio import Event

stop_event = Event()

async def trading_logic(notify):
    await notify("매매 시작")
    while not stop_event.is_set():
        # 여기에 실제 바이비트 매매 로직 넣기
        now = datetime.datetime.now()
        fake_price = round(random.uniform(10000, 11000), 2)
        await notify(f"[{now}] 현재가: {fake_price}")
        await asyncio.sleep(1)
    await notify("매매 종료")

def request_stop():
    stop_event.set()

def reset_stop():
    global stop_event
    stop_event = Event()