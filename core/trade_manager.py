import time
import datetime
import logging
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config_val import session, position, entry_price, SYMBOL, LEVERAGE, MODE
from core.auth import notify

# 현재 포지션 조회
def update_position():
    global position, entry_price
    
    ## 모의 테스트용
    if MODE == "test":
        return
    
    try:
        print(f"포지션 : {position}  평단가 : {entry_price}")
        position["long"] = 0
        position["short"] = 0
        entry_price["long"] = 0.0
        entry_price["short"] = 0.0
        
        pos_data = session.get_positions(category="linear", symbol=SYMBOL)["result"]["list"]
        for p in pos_data:
            side = p.get("side", "").lower()
            size = float(p["size"])
            entry = float(p["avgPrice"]) if size > 0 else 0.0

            if side == "buy":
                position["long"] = size
                entry_price["long"] = entry
            elif side == "sell":
                position["short"] = size
                entry_price["short"] = entry
    except Exception as e:
        logging.error(f"❌ 포지션 업데이트 실패: {e}")

# 진입
async def open_position(side, qty, index):
    
    logging.info(f"→ {side} 진입 요청: {qty}")
    if MODE == "test":
        price = float(entry_price) or 1  # 현재가 기준
        if side == "Buy":
            position["long"] += qty
            entry_price["long"] = price
        elif side == "Sell":
            position["short"] += qty
            entry_price["short"] = price
        logging.info(f"[TEST MODE] 진입 - {side}: {qty}, 진입가: {price}")
        await notify(f"[TEST MODE] 진입 - {side}: {qty}, 진입가: {price}")
        return
    
    
    session.place_order(
        category="linear",
        symbol=SYMBOL,
        side=side,
        order_type="Market",
        qty=qty,
        time_in_force="IOC",
        position_idx=index
    )
    print(f"→ {side} 진입: {qty}")
    await notify(f"→ {side} 진입: {qty}")
    update_position()

# 청산
async def close_position(side, idx):
    side_lower = position[side.lower()]
    qty = position[side_lower]
    if MODE == "test":
        price = float(entry_price) or 1
        logging.info(f"[TEST MODE] 청산 - {side.upper()}: {qty} at {price}")
        await notify(f"[TEST MODE] 청산 - {side.upper()}: {qty} at {price}")
        position[side_lower] = 0
        entry_price[side_lower] = 0
        return
    
    if qty > 0:
        session.place_order(
            category="linear",
            symbol=SYMBOL,
            side="Sell" if side == "long" else "Buy",
            order_type="Market",
            qty=qty,
            reduce_only=True,
            time_in_force="IOC",
            position_idx=idx
        )
        print(f"→ {side} 청산: {qty}")
        await notify(f"→ {side} 청산: {qty}")
        update_position()

# 수익률 계산
def calculate_pnl(price):
    long_pnl = (price - entry_price["long"]) / entry_price["long"] * LEVERAGE * 100 if position["long"] > 0 else 0
    short_pnl = (entry_price["short"] - price) / entry_price["short"] * LEVERAGE * 100 if position["short"] > 0 else 0
    return long_pnl, short_pnl