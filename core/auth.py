# core/auth.py
import time
import json
import hmac
import logging
import telegram
from telegram.request import HTTPXRequest
from config_val import api_key, api_secret, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

request = HTTPXRequest(read_timeout=20.0, connect_timeout=20.0)
telegram_bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN, request=request)

def send_auth():
    expires = int((time.time() + 10) * 1000)
    _val = f'GET/realtime{expires}'
    signature = hmac.new(api_secret.encode(), _val.encode(), digestmod='sha256').hexdigest()
    return json.dumps({
        "op": "auth",
        "args": [api_key, expires, signature]
    })

async def notify(text):
    try:
        await telegram_bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=text)
    except Exception as e:
        logging.info(f"[Telegram Error] {e}")
