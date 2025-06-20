import time
import datetime
import logging
from config_val import session, target_hold_amount
from core.auth import notify

async def place_order_with_tp_sl(order_side, tp_perc=0.011, sl_perc=0.005):
    order = session.place_order(
        category="linear",
        symbol="BTCUSDT",
        side=order_side,
        orderType="Market",
        qty=str(target_hold_amount),
        timeInForce="GTC",
    )
    time.sleep(1)
    positions = session.get_positions(category="linear", symbol="BTCUSDT")
    pos = positions['result']['list'][0]
    base_price = float(pos['avgPrice'])  
    if order_side == "Buy":
        take_profit = round(base_price * (1 + tp_perc), 2)
        stop_loss = round(base_price * (1 - sl_perc), 2)
    else:
        take_profit = round(base_price * (1 - tp_perc), 2)
        stop_loss = round(base_price * (1 + sl_perc), 2)

    session.set_trading_stop(
        category="linear",
        symbol="BTCUSDT",
        takeProfit=str(take_profit),
        stopLoss=str(stop_loss)
    )
    hold_amount = float(pos["size"])
    side = "LONG" if pos["side"] == "Buy" else "SHORT"
    await notify(
        f"{datetime.datetime.now()}\n"
        f"[[[[[[[포지션진입]]]]]]]\n"
        f"[진입가]:{base_price}\n"
        f"[TP]:{take_profit}\n"
        f"[SL]:{stop_loss}\n"
        f"[SIDE]:{side}\n"
        f"[수량]:{pos['size']}\n"
    )
    logging.info(f"{datetime.datetime.now()}\n"
        f"[[[[[[[포지션진입]]]]]]]\n"
        f"[진입가]:{base_price}, TP:{take_profit}, SL:{stop_loss}, SIDE:{side}, 수량:{pos['size']}")
    return hold_amount

def close_position(position_side):

    side = "Sell" if position_side == "Buy" else "Buy"
    logging.info(f"시장가 {side}로 기존 포지션 청산 시도")
    order = session.place_order(
        category="linear",
        symbol="BTCUSDT",
        side=side,
        orderType="Market",
        qty=str(target_hold_amount),
        reduceOnly=True,
        timeInForce="GoodTillCancel"
    )
    logging.info(f"청산 주문결과: {order}")
    return order