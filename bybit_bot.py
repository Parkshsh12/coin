# bybit_bot.py
import asyncio
from asyncio import Event

stop_event = Event()

async def trading_logic(notify):
    while not stop_event.is_set():
        await notify("매매 로직 실행 중...")
        await asyncio.sleep(1)
    await notify("매매 종료됨")

def request_stop():
    stop_event.set()

def reset_stop():
    global stop_event
    stop_event = Event()