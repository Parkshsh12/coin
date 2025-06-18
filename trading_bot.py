import tkinter as tk
import threading
import asyncio
from bybit_trade import main as trading_main  # 방금 만든 파일이름을 bybit_trade.py라고 가정

class TradingApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Bybit Trading Bot")

        self.status_label = tk.Label(root, text="상태: 대기 중", font=("Arial", 12))
        self.status_label.pack(pady=10)

        self.start_button = tk.Button(root, text="▶️ 매매 시작", command=self.start_trading, bg="green", fg="white", width=20)
        self.start_button.pack(pady=5)

        self.stop_button = tk.Button(root, text="⏹️ 매매 중지 (비동기 취소 불가)", state=tk.DISABLED, bg="gray", fg="white", width=20)
        self.stop_button.pack(pady=5)

        self.trading_thread = None

    def start_trading(self):
        self.status_label.config(text="상태: 매매 중")
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)

        self.trading_thread = threading.Thread(target=self.run_async_loop)
        self.trading_thread.start()

    def run_async_loop(self):
        try:
            asyncio.run(trading_main())
        except Exception as e:
            self.status_label.config(text=f"오류 발생: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = TradingApp(root)
    root.mainloop()
