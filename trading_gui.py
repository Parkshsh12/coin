# trading_gui.py
import tkinter as tk
import threading
import asyncio
import bybit_trade  # 위의 코드를 bybit_bot.py로 저장했다고 가정

class TradingApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Bybit 트레이딩 봇")
        self.status = tk.StringVar(value="🟡 대기 중")

        self.status_label = tk.Label(root, textvariable=self.status, font=("Arial", 12))
        self.status_label.pack(pady=10)

        self.text_area = tk.Text(root, height=12, width=60, state=tk.DISABLED)
        self.text_area.pack(pady=10)

        self.start_button = tk.Button(root, text="▶️ 매매 시작", command=self.start_bot, bg="green", fg="white")
        self.start_button.pack(pady=5)

        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self.loop.run_forever, daemon=True)
        self.thread.start()

    def start_bot(self):
        self.status.set("🟢 매매 중")
        self.start_button.config(state=tk.DISABLED)
        asyncio.run_coroutine_threadsafe(self.run_bot(), self.loop)

    async def run_bot(self):
        try:
            await bybit_trade.main()
        except Exception as e:
            self.status.set("🔴 오류 발생")
            self.append_text(f"❗ 예외 발생: {e}")

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