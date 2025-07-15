import time
import datetime
import logging
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config_val import session, position, entry_price, SYMBOL, LEVERAGE
from core.auth import notify

# 현재 포지션 조회
def update_position():
    global position, entry_price
    try:
        position["long"] = 0
        position["short"] = 0
        entry_price["long"] = 0.0
        entry_price["short"] = 0.0
        
        pos_data = session.get_positions(category="linear", symbol=SYMBOL)["result"]["list"]
        print(pos_data)
        print(position)
        for p in pos_data:
            side = p.get("side", "").lower()
            print(f"{p.get('side', '').lower()} sideside")
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
def open_position(side, qty, index):
    print(side)
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
    notify(f"→ {side} 진입: {qty}")
    update_position()

# 청산
def close_position(side, idx):
    qty = position[side.lower()]
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
        notify(f"→ {side} 청산: {qty}")
        update_position()

# 수익률 계산
def calculate_pnl(price):
    long_pnl = (price - entry_price["long"]) / entry_price["long"] * LEVERAGE if position["long"] > 0 else 0
    short_pnl = (entry_price["short"] - price) / entry_price["short"] * LEVERAGE if position["short"] > 0 else 0
    return long_pnl, short_pnl