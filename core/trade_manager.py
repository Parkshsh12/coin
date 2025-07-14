import time
import datetime
import logging
from config_val import session, position, entry_price, SYMBOL, LEVERAGE
from core.auth import notify

# 현재 포지션 조회
def update_position():
    global position, entry_price
    pos_data = session.get_positions(category="linear", symbol=SYMBOL)["result"]["list"]
    for p in pos_data:
        side = p["side"].lower()
        size = float(p["size"])
        entry = float(p["entryPrice"]) if size > 0 else 0.0
        if side == "buy":
            position["long"] = size
            entry_price["long"] = entry
        elif side == "sell":
            position["short"] = size
            entry_price["short"] = entry

# 진입
def open_position(side, qty):
    session.place_order(
        category="linear",
        symbol=SYMBOL,
        side=side,
        order_type="Market",
        qty=qty,
        time_in_force="IOC"
    )
    print(f"→ {side} 진입: {qty}")
    notify(f"→ {side} 진입: {qty}")
    update_position()

# 청산
def close_position(side):
    qty = position[side.lower()]
    if qty > 0:
        session.place_order(
            category="linear",
            symbol=SYMBOL,
            side="Sell" if side == "long" else "Buy",
            order_type="Market",
            qty=qty,
            reduce_only=True,
            time_in_force="IOC"
        )
        print(f"× {side.upper()} 청산: {qty}")
        update_position()

# 수익률 계산
def calculate_pnl(price):
    long_pnl = (price - entry_price["long"]) / entry_price["long"] * LEVERAGE if position["long"] > 0 else 0
    short_pnl = (entry_price["short"] - price) / entry_price["short"] * LEVERAGE if position["short"] > 0 else 0
    return long_pnl, short_pnl