import sys
import os
import json
import datetime
import subprocess
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QTextEdit, QHBoxLayout
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont

class TradingGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("📈 Bybit 자동매매")
        self.setGeometry(200, 200, 600, 700)
        layout = QVBoxLayout()

        # API Key
        api_key_row = QHBoxLayout()
        api_key_label = QLabel("API Key:")
        self.api_key_input = QLineEdit()
        api_key_row.addWidget(api_key_label)
        api_key_row.addWidget(self.api_key_input)
        layout.addLayout(api_key_row)

        # API Secret
        api_secret_row = QHBoxLayout()
        api_secret_label = QLabel("API Secret:")
        self.api_secret_input = QLineEdit()
        api_secret_row.addWidget(api_secret_label)
        api_secret_row.addWidget(self.api_secret_input)
        layout.addLayout(api_secret_row)

        # Telegram Token
        telegram_token_row = QHBoxLayout()
        telegram_token_label = QLabel("Telegram Bot Token:")
        self.telegram_token_input = QLineEdit()
        telegram_token_row.addWidget(telegram_token_label)
        telegram_token_row.addWidget(self.telegram_token_input)
        layout.addLayout(telegram_token_row)

        # Telegram Chat ID
        telegram_chat_row = QHBoxLayout()
        telegram_chat_label = QLabel("Telegram Chat ID:")
        self.telegram_chat_input = QLineEdit()
        telegram_chat_row.addWidget(telegram_chat_label)
        telegram_chat_row.addWidget(self.telegram_chat_input)
        layout.addLayout(telegram_chat_row)

        # 투입 금액
        amount_row = QHBoxLayout()
        amount_label = QLabel("투입 금액 (USDT):")
        self.amount_input = QLineEdit()
        amount_row.addWidget(amount_label)
        amount_row.addWidget(self.amount_input)
        layout.addLayout(amount_row)

        # 버튼들
        self.save_btn = QPushButton("🔒 설정 저장")
        self.save_btn.clicked.connect(self.save_config)
        layout.addWidget(self.save_btn)

        self.start_btn = QPushButton("🚀 자동매매 시작")
        self.start_btn.clicked.connect(self.start_trading)
        layout.addWidget(self.start_btn)

        self.stop_btn = QPushButton("❌ 자동매매 종료")
        self.stop_btn.clicked.connect(self.stop_trading)
        layout.addWidget(self.stop_btn)

        # 로그 출력
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        layout.addWidget(QLabel("📋 실시간 로그"))
        layout.addWidget(self.log_output)

        self.setLayout(layout)

        # 설정
        self.running = False
        self.config_path = "config/user_config.json"
        self.log_date = datetime.datetime.now().strftime("%Y-%m-%d")
        self.log_path = f"log/log_{self.log_date}.txt"
        self.process = None
        self.last_log_line = 0
        self.load_config()

        # 로그 로딩 타이머
        self.timer = QTimer()
        self.timer.timeout.connect(self.load_log_file)
        self.timer.start(3000)

    def append_log(self, text):
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        self.log_output.append(f"[{timestamp}] {text}")
        self.log_output.moveCursor(self.log_output.textCursor().End)
        self.log_output.ensureCursorVisible()

    def save_config(self):
        config = {
            "API_KEY": self.api_key_input.text(),
            "API_SECRET": self.api_secret_input.text(),
            "TELEGRAM_BOT_TOKEN": self.telegram_token_input.text(),
            "TELEGRAM_CHAT_ID": self.telegram_chat_input.text(),
            "TRADE_AMOUNT": self.amount_input.text()
        }
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(config, f)
        self.append_log("✅ 설정 저장 완료")

    def load_config(self):
        if os.path.exists(self.config_path):
            with open(self.config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
                self.api_key_input.setText(config.get("API_KEY", ""))
                self.api_secret_input.setText(config.get("API_SECRET", ""))
                self.telegram_token_input.setText(config.get("TELEGRAM_BOT_TOKEN", ""))
                self.telegram_chat_input.setText(config.get("TELEGRAM_CHAT_ID", ""))
                self.amount_input.setText(config.get("TRADE_AMOUNT", ""))

    def start_trading(self):
        if not os.path.exists("bybit_trade.py"):
            self.append_log("❌ bybit_trade.py 파일이 없습니다")
            return
        self.save_config()
        env = os.environ.copy()
        with open(self.config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        env.update(config)

        self.process = subprocess.Popen(
            [sys.executable, "bybit_trade.py"],
            env=env
        )
        self.running = True
        self.timer.start(3000)
        self.append_log("🚀 거래 스크립트 실행 중...")

    def stop_trading(self):
        if self.process and self.process.poll() is None:
            self.running = False
            self.process.terminate()
            self.timer.stop()  # 로그 읽기 타이머 정지
            self.append_log("🛑 거래 스크립트 종료됨")
            self.process = None
        else:
            self.append_log("⚠️ 실행 중인 거래가 없습니다")

    def load_log_file(self):
        if not self.running:
            return
        if os.path.exists(self.log_path):
            with open(self.log_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
                new_lines = lines[self.last_log_line:]
                for line in new_lines:
                    self.log_output.append(line.strip())
                    self.log_output.moveCursor(self.log_output.textCursor().End)
                    self.log_output.ensureCursorVisible()
                self.last_log_line = len(lines)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    if sys.platform == "darwin":
        app.setFont(QFont("AppleGothic", 10))
    elif sys.platform.startswith("win"):
        app.setFont(QFont("Malgun Gothic", 10))
    win = TradingGUI()
    win.show()
    sys.exit(app.exec_())
