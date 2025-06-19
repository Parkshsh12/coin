import asyncio
import websockets
import json
import hmac
from datetime import datetime, timedelta
import time


class Main:
    def send_auth(self):
        api_key = 'uobPGl5Ol3lBSqztB8'
        api_secret = 'SubtOb7Cwti2Bdan10gjNfkSe6ZZtbEhlcZL'
        expires = int((time.time() + 10) * 1000)
        _val = f'GET/realtime{expires}'
        signature = hmac.new(
            api_secret.encode(),
            _val.encode(),
            digestmod='sha256'
        ).hexdigest()
        return json.dumps({
            "op": "auth",
            "args": [api_key, expires, signature]
        })

    # Private WebSocket
    async def bybit_private_ws(self):
        while True:
            try:
                async with websockets.connect("wss://stream-testnet.bybit.com/v5/private?max_active_time=10m") as ws_private:
                    print("✅ Private WebSocket 연결됨")
                    await ws_private.send(self.send_auth())  # () 붙여야 됨!
                    await ws_private.send(json.dumps({
                        "op": "subscribe",
                        "args": ["position", "execution", "order", "wallet"]
                    }))

                    while True:
                        data_rcv_strjson = await ws_private.recv()
                        rawdata = json.loads(data_rcv_strjson)
                        print("📥 [PRIVATE]", rawdata)

            except websockets.ConnectionClosed:
                print("❌ Private WebSocket 연결 끊김, 재연결 시도 중...")
                await asyncio.sleep(3)

    # Public WebSocket
    async def bybit_public_ws(self):
        while True:
            try:
                async with websockets.connect("wss://stream-testnet.bybit.com/v5/public/linear") as ws_public:
                    print("✅ Public WebSocket 연결됨")
                    await ws_public.send(json.dumps({
                        "op": "subscribe",
                        "args": ["publicTrade.BTCUSDT"]
                    }))

                    send_ping_time = datetime.now()
                    send_ping_process = False

                    while True:
                        data_rcv_strjson = await ws_public.recv()
                        rawdata = json.loads(data_rcv_strjson)
                        print("📥 [PUBLIC]", rawdata)

                        if rawdata.get('ret_msg') == 'pong':
                            send_ping_process = False
                            send_ping_time = datetime.now()

                        # 20초마다 ping 전송
                        if datetime.now() - send_ping_time > timedelta(seconds=20) and not send_ping_process:
                            await ws_public.send(json.dumps({
                                "req_id": "public_ping",
                                "op": "ping"
                            }))
                            send_ping_process = True

            except websockets.ConnectionClosed:
                print("❌ Public WebSocket 연결 끊김, 재연결 시도 중...")
                await asyncio.sleep(3)

    # asyncio 시작점
    async def start_websocket(self):
        await asyncio.gather(
            self.bybit_public_ws(),
            self.bybit_private_ws()
        )


if __name__ == "__main__":
    main = Main()
    asyncio.run(main.start_websocket())
