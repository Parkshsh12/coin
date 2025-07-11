import pandas as pd
import numpy as np
import torch
import torch.nn as nn
from sklearn.preprocessing import MinMaxScaler
from torch.utils.data import DataLoader, Dataset
import matplotlib.pyplot as plt

# 1. 데이터 생성
np.random.seed(42)
n = 1000
price = np.linspace(30000, 35000, n) + np.random.normal(0, 300, n)
df = pd.DataFrame({'close': price})

# 2. 정규화
scaler = MinMaxScaler()
df['scaled_close'] = scaler.fit_transform(df[['close']])

# 3. PyTorch Dataset 정의
class PriceDataset(Dataset):
    def __init__(self, series, seq_len):
        self.X, self.y = [], []
        for i in range(len(series) - seq_len - 1):
            self.X.append(series[i:i+seq_len])
            self.y.append(series[i+seq_len])
        self.X = torch.tensor(self.X).float()
        self.y = torch.tensor(self.y).float()

    def __len__(self):
        return len(self.X)

    def __getitem__(self, idx):
        return self.X[idx], self.y[idx]

SEQ_LEN = 20
dataset = PriceDataset(df['scaled_close'].values, SEQ_LEN)
train_size = int(len(dataset) * 0.8)
train_dataset = torch.utils.data.Subset(dataset, range(train_size))
test_dataset = torch.utils.data.Subset(dataset, range(train_size, len(dataset)))
train_loader = DataLoader(train_dataset, batch_size=32)
test_loader = DataLoader(test_dataset, batch_size=1)

# 4. Transformer 모델 정의
class TransformerModel(nn.Module):
    def __init__(self, seq_len):
        super().__init__()
        self.embedding = nn.Linear(1, 64)
        encoder_layer = nn.TransformerEncoderLayer(d_model=64, nhead=8)
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=2)
        self.fc = nn.Linear(64 * seq_len, 1)

    def forward(self, x):
        x = x.unsqueeze(-1)  # (B, T) -> (B, T, 1)
        x = self.embedding(x)  # (B, T, 64)
        x = x.permute(1, 0, 2)  # (T, B, 64)
        x = self.transformer(x)  # (T, B, 64)
        x = x.permute(1, 0, 2).reshape(x.size(1), -1)  # (B, T*64)
        return self.fc(x).squeeze()

model = TransformerModel(seq_len=SEQ_LEN)
criterion = nn.MSELoss()
optimizer = torch.optim.Adam(model.parameters(), lr=0.001)

# 5. 학습
model.train()
for epoch in range(5):
    for X_batch, y_batch in train_loader:
        optimizer.zero_grad()
        preds = model(X_batch)
        loss = criterion(preds, y_batch)
        loss.backward()
        optimizer.step()

# 6. 예측 및 백테스트
model.eval()
preds, trues = [], []
with torch.no_grad():
    for X_batch, y_batch in test_loader:
        pred = model(X_batch).item()
        preds.append(pred)
        trues.append(y_batch.item())

preds = scaler.inverse_transform(np.array(preds).reshape(-1, 1)).flatten()
trues = scaler.inverse_transform(np.array(trues).reshape(-1, 1)).flatten()
entry_price = scaler.inverse_transform(np.array([x[-1] for x, _ in test_dataset]).reshape(-1, 1)).flatten()

# 7. 전략 수익 계산 (롱/숏 전략)
signal = np.where(preds > entry_price, 1, -1)  # 예측 > 현재가 → 롱(1), 아니면 숏(-1)
strategy_return = signal * ((trues - entry_price) / entry_price)
cumulative_return = (1 + strategy_return).cumprod()

# 시각화
plt.plot(cumulative_return, label="Transformer 전략 수익률")
plt.title("📈 Transformer 기반 자동매매 전략 백테스트")
plt.xlabel("시간")
plt.ylabel("누적 수익률")
plt.grid()
plt.legend()
plt.show()
