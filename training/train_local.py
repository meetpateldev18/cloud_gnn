"""
Quick training script for local development.
Generates synthetic data and trains a small model for testing.
"""

import os
import sys
import numpy as np
import random
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.optim import Adam

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from torch_geometric.nn import GATConv
except ImportError:
    print("ERROR: torch_geometric not installed. Run: pip install torch-geometric")
    sys.exit(1)

from backend.scheduler import GATScheduler

SEED = 42
NUM_MACHINES = 20
EPOCHS = 30
BATCH_SIZE = 32
LR = 0.001
N_TASKS = 5000

random.seed(SEED)
np.random.seed(SEED)
torch.manual_seed(SEED)

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"Device: {device}")

# Synthetic features
machine_features = np.random.rand(NUM_MACHINES, 4).astype(np.float32)

# Edges
src, dst = [], []
for i in range(NUM_MACHINES):
    for j in range(NUM_MACHINES):
        if i != j and (abs(i - j) <= 3 or random.random() < 0.2):
            src.append(i)
            dst.append(j)
edge_index = torch.tensor([src, dst], dtype=torch.long).to(device)

# Task data
task_features = np.random.rand(N_TASKS, 4).astype(np.float32)
labels = np.array([
    int(np.argmax([(machine_features[j, 0] * (1 - machine_features[j, 2]) - task_features[i, 0])
                    + (machine_features[j, 1] - task_features[i, 1])
                    for j in range(NUM_MACHINES)]))
    for i in range(N_TASKS)
], dtype=np.int64)

split = int(0.8 * N_TASKS)

model = GATScheduler(num_machines=NUM_MACHINES).to(device)
optimizer = Adam(model.parameters(), lr=LR)
criterion = nn.CrossEntropyLoss()
x = torch.tensor(machine_features).to(device)

print("Training...")
for epoch in range(1, EPOCHS + 1):
    model.train()
    idx = np.random.permutation(split)
    total_loss = 0
    for s in range(0, split, BATCH_SIZE):
        b = idx[s:s + BATCH_SIZE]
        t = torch.tensor(task_features[b]).to(device)
        y = torch.tensor(labels[b]).to(device)
        optimizer.zero_grad()
        out = model(x, edge_index, t)
        loss = criterion(out, y)
        loss.backward()
        optimizer.step()
        total_loss += loss.item()

    if epoch % 5 == 0:
        model.eval()
        with torch.no_grad():
            t_val = torch.tensor(task_features[split:]).to(device)
            y_val = torch.tensor(labels[split:]).to(device)
            acc = (model(x, edge_index, t_val).argmax(1) == y_val).float().mean().item()
        print(f"  Epoch {epoch:2d} | Loss: {total_loss / (split // BATCH_SIZE):.4f} | Val Acc: {acc:.4f}")

os.makedirs("model", exist_ok=True)
torch.save(model.state_dict(), "model/scheduler_model.pt")
print("\nModel saved to model/scheduler_model.pt")
