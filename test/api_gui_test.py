import sys
import os
import asyncio
import json
import datetime
import subprocess
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QTextEdit, QFileDialog, QMessageBox
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import threading

class TradingGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("📈 Bybit 자동매매")
        self.setGeometry(200, 200, 600, 700)
        layout = QVBoxLayout()

        self.api_key_input = QLineEdit()
        self.api_key_input.setPlaceholderText("API Key")
        layout.addWidget(self.api_key_input)

        self.api_secret_input = QLineEdit()
        self.api_secret_input.setPlaceholderText("API Secret")
        layout.addWidget(self.api_secret_input)

        self.telegram_token_input = QLineEdit()
        self.telegram_token_input.setPlaceholderText("Telegram Bot Token")
        layout.addWidget(self.telegram_token_input)

        self.telegram_chat_input = QLineEdit()
        self.telegram_chat_input.setPlaceholderText("Telegram Chat ID")
        layout.addWidget(self.telegram_chat_input)

        self.save_btn = QPushButton("🔒 설정 저장")
        self.save_btn.clicked.connect(self.save_config)
        layout.addWidget(self.save_btn)

        self.start_btn = QPushButton("🚀 자동매매 시작")
        self.start_btn.clicked.connect(self.start_trading)
        layout.addWidget(self.start_btn)

        self.stop_btn = QPushButton("❌ 자동매매 종료")
        self.stop_btn.clicked.connect(self.stop_trading)
        layout.addWidget(self.stop_btn)

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        layout.addWidget(QLabel("📋 실시간 로그"))
        layout.addWidget(self.log_output)

        self.setLayout(layout)
        self.timer = QTimer()
        self.timer.start(5000)

        self.config_path = "user_config.json"
        self.profit_log_path = "profit_log.json"
        self.process = None  # 거래 프로세스 저장용
        self.load_config()

    def append_log(self, text):
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        self.log_output.append(f"[{timestamp}] {text}")

    def save_config(self):
        config = {
            "API_KEY": self.api_key_input.text(),
            "API_SECRET": self.api_secret_input.text(),
            "TELEGRAM_BOT_TOKEN": self.telegram_token_input.text(),
            "TELEGRAM_CHAT_ID": self.telegram_chat_input.text()
        }
        with open(self.config_path, "w") as f:
            json.dump(config, f)
        self.append_log("✅ 설정 저장 완료")

    def load_config(self):
        if os.path.exists(self.config_path):
            with open(self.config_path, "r") as f:
                config = json.load(f)
                self.api_key_input.setText(config.get("API_KEY", ""))
                self.api_secret_input.setText(config.get("API_SECRET", ""))
                self.telegram_token_input.setText(config.get("TELEGRAM_BOT_TOKEN", ""))
                self.telegram_chat_input.setText(config.get("TELEGRAM_CHAT_ID", ""))

    def start_trading(self):
        if not os.path.exists("bybit_trade.py"):
            self.append_log("❌ bybit_trade.py 파일이 없습니다")
            return
        self.save_config()
        env = os.environ.copy()
        with open(self.config_path, "r") as f:
            config = json.load(f)
        env.update(config)
        self.process = subprocess.Popen(
            [sys.executable, "bybit_trade.py"],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )

        self.append_log("🚀 거래 스크립트 실행 중...")
        threading.Thread(target=self.read_stdout, daemon=True).start()

    def stop_trading(self):
        if self.process and self.process.poll() is None:
            self.process.terminate()
            self.append_log("🛑 거래 스크립트 종료됨")
            self.process = None
        else:
            self.append_log("⚠️ 실행 중인 거래가 없습니다")
            
    def read_stdout(self):
        if self.process and self.process.stdout:
            for line in self.process.stdout:
                self.append_log(line.strip())
if __name__ == "__main__":
    app = QApplication(sys.argv)
    if sys.platform == "darwin":  # macOS
        app.setFont(QFont("AppleGothic", 10))  # ← 크기 조정 (예: 10)
    elif sys.platform.startswith("win"):  # Windows
        app.setFont(QFont("Malgun Gothic", 10))  # ← 크기 조정 (예: 10)
    win = TradingGUI()
    win.show()
    sys.exit(app.exec_())