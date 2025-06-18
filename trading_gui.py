# trading_gui.py
import tkinter as tk
import threading
import asyncio
from bybit_bot import trading_logic, request_stop, reset_stop

class TradingApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Bybit 트레이딩 봇")
        self.status = tk.StringVar(value="🟡 대기 중")

        self.status_label = tk.Label(root, textvariable=self.status, font=("Arial", 12))
        self.status_label.pack(pady=10)

        self.text_area = tk.Text(root, height=10, width=50, state=tk.DISABLED)
        self.text_area.pack(pady=10)

        self.start_button = tk.Button(root, text="▶️ 매매 시작", command=self.start_bot, bg="green", fg="white")
        self.start_button.pack(pady=5)

        self.stop_button = tk.Button(root, text="⏹️ 매매 중지", command=self.stop_bot, bg="red", fg="white", state=tk.DISABLED)
        self.stop_button.pack(pady=5)

        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self.loop.run_forever, daemon=True)
        self.thread.start()

    def start_bot(self):
        self.status.set("🟢 매매 중")
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        reset_stop()

        asyncio.run_coroutine_threadsafe(trading_logic(self.append_text), self.loop)

    def stop_bot(self):
        request_stop()
        self.status.set("🔴 중지 요청됨")
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)

    def append_text(self, msg):
        def _append():
            self.text_area.config(state=tk.NORMAL)
            self.text_area.insert(tk.END, msg + "\n")
            self.text_area.config(state=tk.DISABLED)
            self.text_area.see(tk.END)
        self.root.after(0, _append)

if __name__ == "__main__":
    root = tk.Tk()
    app = TradingApp(root)
    root.mainloop()