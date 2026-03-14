"""
=============================================================================
 GNN Task Scheduler — Kaggle Training Pipeline
=============================================================================
 This script is designed to run on a Kaggle GPU notebook.

 Steps:
   1. Load Google Cluster Workload Trace dataset
   2. Perform feature engineering
   3. Construct cloud infrastructure graph
   4. Train a Graph Attention Network (GAT) scheduler
   5. Evaluate and save model weights

 Usage on Kaggle:
   - Create a new notebook
   - Enable GPU: Settings → Accelerator → GPU T4 x2
   - Upload dataset or add from Kaggle datasets
   - Paste this script into a cell and run
=============================================================================
"""

import os
import random
import numpy as np
import pandas as pd
import networkx as nx
from collections import defaultdict

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.optim import Adam
from torch.optim.lr_scheduler import CosineAnnealingLR

try:
    from torch_geometric.nn import GATConv
    from torch_geometric.data import Data, Batch
    print("[OK] torch_geometric available")
except ImportError:
    print("Installing torch_geometric...")
    os.system("pip install torch-geometric")
    from torch_geometric.nn import GATConv
    from torch_geometric.data import Data, Batch

# =====================  CONFIG  =====================
DATASET_DIR = "/kaggle/input/google-2019-cluster-sample"  # Kaggle default path
# If running locally, change to:
# DATASET_DIR = "./dataset"

NUM_MACHINES = 20        # Virtual machines to simulate
HIDDEN_DIM = 64
HEADS = 4
EPOCHS = 100
BATCH_SIZE = 64
LR = 0.001
SEED = 42

random.seed(SEED)
np.random.seed(SEED)
torch.manual_seed(SEED)

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"Using device: {device}")

# =====================  DATASET LOADING  =====================
print("\n--- Loading Dataset ---")

# Try multiple possible file patterns
def load_csv(name, possible_suffixes=None):
    """Try to load a CSV with different naming patterns."""
    if possible_suffixes is None:
        possible_suffixes = ["", "_part-00000-of-00001"]
    
    for suffix in possible_suffixes:
        path = os.path.join(DATASET_DIR, f"{name}{suffix}.csv")
        if os.path.isfile(path):
            print(f"  Loaded: {path}")
            return pd.read_csv(path, nrows=500000)  # Limit rows for memory
    
    # Try to find any file with the name pattern
    if os.path.isdir(DATASET_DIR):
        for f in os.listdir(DATASET_DIR):
            if name in f.lower() and f.endswith('.csv'):
                path = os.path.join(DATASET_DIR, f)
                print(f"  Loaded: {path}")
                return pd.read_csv(path, nrows=500000)
    
    print(f"  [WARN] Could not find {name} CSV – generating synthetic data")
    return None


machine_df = load_csv("machine_events")
task_df = load_csv("task_events")
job_df = load_csv("job_events")

# =====================  SYNTHETIC FALLBACK  =====================
# If dataset files are not available, generate synthetic training data

if machine_df is None:
    print("\n--- Generating Synthetic Machine Data ---")
    machine_df = pd.DataFrame({
        "machine_id": [f"machine_{i}" for i in range(NUM_MACHINES)],
        "cpu_capacity": np.random.uniform(2, 16, NUM_MACHINES),
        "memory_capacity": np.random.uniform(4, 64, NUM_MACHINES),
    })

if task_df is None:
    print("--- Generating Synthetic Task Data ---")
    n_tasks = 10000
    task_df = pd.DataFrame({
        "job_id": np.random.randint(0, 1000, n_tasks),
        "task_index": np.arange(n_tasks),
        "machine_id": np.random.choice([f"machine_{i}" for i in range(NUM_MACHINES)], n_tasks),
        "cpu_request": np.random.uniform(0.1, 4.0, n_tasks),
        "memory_request": np.random.uniform(0.5, 16.0, n_tasks),
        "priority": np.random.randint(0, 10, n_tasks),
    })

# =====================  FEATURE ENGINEERING  =====================
print("\n--- Feature Engineering ---")

# Normalize column names (Google traces use numeric column indices)
if "machine_id" not in machine_df.columns and len(machine_df.columns) >= 3:
    machine_df.columns = ["timestamp", "machine_id", "event_type"] + \
        [f"col_{i}" for i in range(3, len(machine_df.columns))]
    if len(machine_df.columns) >= 5:
        machine_df = machine_df.rename(columns={"col_3": "cpu_capacity", "col_4": "memory_capacity"})

if "cpu_request" not in task_df.columns and len(task_df.columns) >= 10:
    col_names = ["timestamp", "missing_info", "job_id", "task_index", "machine_id",
                 "event_type", "user", "scheduling_class", "priority", "cpu_request",
                 "memory_request", "disk_space_request", "different_machines_restriction"]
    task_df.columns = col_names[:len(task_df.columns)] + \
        [f"col_{i}" for i in range(len(col_names), len(task_df.columns))]

# Ensure numeric types
for col in ["cpu_capacity", "memory_capacity"]:
    if col in machine_df.columns:
        machine_df[col] = pd.to_numeric(machine_df[col], errors="coerce")

for col in ["cpu_request", "memory_request", "priority"]:
    if col in task_df.columns:
        task_df[col] = pd.to_numeric(task_df[col], errors="coerce")

# Fill NaN
machine_df = machine_df.fillna(0)
task_df = task_df.fillna(0)

# Get unique machines
if "cpu_capacity" in machine_df.columns:
    machines = machine_df.drop_duplicates(subset=["machine_id"]).head(NUM_MACHINES)
else:
    machines = pd.DataFrame({
        "machine_id": [f"machine_{i}" for i in range(NUM_MACHINES)],
        "cpu_capacity": np.random.uniform(2, 16, NUM_MACHINES),
        "memory_capacity": np.random.uniform(4, 64, NUM_MACHINES),
    })

# Machine features: [cpu_capacity, memory_capacity, current_load, network_bandwidth]
machine_features = np.zeros((NUM_MACHINES, 4), dtype=np.float32)
for i in range(min(NUM_MACHINES, len(machines))):
    row = machines.iloc[i]
    machine_features[i, 0] = float(row.get("cpu_capacity", np.random.uniform(2, 16)))
    machine_features[i, 1] = float(row.get("memory_capacity", np.random.uniform(4, 64)))
    machine_features[i, 2] = np.random.uniform(0.05, 0.7)  # Simulated current load
    machine_features[i, 3] = np.random.uniform(1, 10)        # Simulated bandwidth

# Normalize features
for j in range(4):
    col_max = machine_features[:, j].max()
    if col_max > 0:
        machine_features[:, j] /= col_max

print(f"  Machine features shape: {machine_features.shape}")

# =====================  GRAPH CONSTRUCTION  =====================
print("\n--- Constructing Cloud Infrastructure Graph ---")

G = nx.Graph()
for i in range(NUM_MACHINES):
    G.add_node(i)

# Ring + random topology
for i in range(NUM_MACHINES):
    G.add_edge(i, (i + 1) % NUM_MACHINES)
# Add random extra edges
for _ in range(NUM_MACHINES * 2):
    a, b = random.sample(range(NUM_MACHINES), 2)
    G.add_edge(a, b)

edges = list(G.edges())
edge_index = torch.tensor(
    [[e[0] for e in edges] + [e[1] for e in edges],
     [e[1] for e in edges] + [e[0] for e in edges]],
    dtype=torch.long,
)
print(f"  Nodes: {G.number_of_nodes()}, Edges: {G.number_of_edges()}")
print(f"  edge_index shape: {edge_index.shape}")

# =====================  TRAINING DATA  =====================
print("\n--- Preparing Training Data ---")

# For each task, the "label" is the best machine (simulated optimal assignment)
task_features_list = []
labels_list = []

n_samples = min(len(task_df), 20000)
sample_tasks = task_df.sample(n=n_samples, random_state=SEED).reset_index(drop=True)

for idx in range(n_samples):
    row = sample_tasks.iloc[idx]
    cpu_req = float(row.get("cpu_request", np.random.uniform(0.1, 2.0)))
    mem_req = float(row.get("memory_request", np.random.uniform(0.5, 8.0)))
    prio = int(row.get("priority", 0))
    arrival = idx / n_samples  # Normalized arrival time

    task_feat = [cpu_req, mem_req, prio / 10.0, arrival]
    task_features_list.append(task_feat)

    # Optimal machine: best fit based on remaining capacity
    scores = []
    for j in range(NUM_MACHINES):
        cpu_cap = machine_features[j, 0] * 16  # Denormalize approx
        mem_cap = machine_features[j, 1] * 64
        load = machine_features[j, 2]
        remaining = (cpu_cap * (1 - load) - cpu_req) + (mem_cap - mem_req)
        # Penalize overloaded machines
        if cpu_cap * (1 - load) < cpu_req:
            remaining -= 100
        scores.append(remaining)
    labels_list.append(int(np.argmax(scores)))

task_features = np.array(task_features_list, dtype=np.float32)
labels = np.array(labels_list, dtype=np.int64)

# Normalize task features
for j in range(task_features.shape[1]):
    col_max = task_features[:, j].max()
    if col_max > 0:
        task_features[:, j] /= col_max

print(f"  Task features shape: {task_features.shape}")
print(f"  Labels shape: {labels.shape}")
print(f"  Label distribution (top 5): {pd.Series(labels).value_counts().head()}")

# Train/val split
split = int(0.8 * n_samples)
train_tasks, val_tasks = task_features[:split], task_features[split:]
train_labels, val_labels = labels[:split], labels[split:]

# =====================  MODEL DEFINITION  =====================
print("\n--- Building GAT Model ---")


class GATScheduler(nn.Module):
    def __init__(self, node_features=4, task_features=4, hidden_dim=64, heads=4, num_machines=20):
        super().__init__()
        self.gat1 = GATConv(node_features, hidden_dim, heads=heads, concat=True)
        self.gat2 = GATConv(hidden_dim * heads, hidden_dim, heads=1, concat=False)
        self.task_encoder = nn.Sequential(
            nn.Linear(task_features, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
        )
        self.classifier = nn.Sequential(
            nn.Linear(hidden_dim * 2, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, 1),
        )
        self.num_machines = num_machines

    def forward(self, x, edge_index, task_feat):
        h = F.elu(self.gat1(x, edge_index))
        h = F.elu(self.gat2(h, edge_index))

        t = self.task_encoder(task_feat)

        batch_size = t.size(0)
        num_nodes = h.size(0)
        h_exp = h.unsqueeze(0).expand(batch_size, -1, -1)
        t_exp = t.unsqueeze(1).expand(-1, num_nodes, -1)
        combined = torch.cat([h_exp, t_exp], dim=-1)
        scores = self.classifier(combined).squeeze(-1)
        return scores


model = GATScheduler(
    node_features=4,
    task_features=4,
    hidden_dim=HIDDEN_DIM,
    heads=HEADS,
    num_machines=NUM_MACHINES,
).to(device)

total_params = sum(p.numel() for p in model.parameters())
print(f"  Total parameters: {total_params:,}")

# =====================  TRAINING  =====================
print("\n--- Training ---")

x = torch.tensor(machine_features, dtype=torch.float32).to(device)
ei = edge_index.to(device)

optimizer = Adam(model.parameters(), lr=LR, weight_decay=1e-5)
scheduler = CosineAnnealingLR(optimizer, T_max=EPOCHS)
criterion = nn.CrossEntropyLoss()

best_val_acc = 0.0
train_losses = []
val_accs = []

for epoch in range(1, EPOCHS + 1):
    model.train()
    epoch_loss = 0.0
    n_batches = 0

    indices = np.random.permutation(len(train_tasks))
    for start in range(0, len(train_tasks), BATCH_SIZE):
        batch_idx = indices[start:start + BATCH_SIZE]
        t_batch = torch.tensor(train_tasks[batch_idx], dtype=torch.float32).to(device)
        y_batch = torch.tensor(train_labels[batch_idx], dtype=torch.long).to(device)

        optimizer.zero_grad()
        scores = model(x, ei, t_batch)
        loss = criterion(scores, y_batch)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
        optimizer.step()

        epoch_loss += loss.item()
        n_batches += 1

    scheduler.step()
    avg_loss = epoch_loss / max(n_batches, 1)
    train_losses.append(avg_loss)

    # Validation
    model.eval()
    with torch.no_grad():
        t_val = torch.tensor(val_tasks, dtype=torch.float32).to(device)
        y_val = torch.tensor(val_labels, dtype=torch.long).to(device)
        val_scores = model(x, ei, t_val)
        val_preds = val_scores.argmax(dim=1)
        val_acc = (val_preds == y_val).float().mean().item()
        val_accs.append(val_acc)

    if val_acc > best_val_acc:
        best_val_acc = val_acc
        torch.save(model.state_dict(), "scheduler_model.pt")

    if epoch % 10 == 0 or epoch == 1:
        print(f"  Epoch {epoch:3d}/{EPOCHS} | Loss: {avg_loss:.4f} | Val Acc: {val_acc:.4f} | Best: {best_val_acc:.4f}")

print(f"\n  Training complete. Best validation accuracy: {best_val_acc:.4f}")
print(f"  Model saved to: scheduler_model.pt")

# =====================  EVALUATION  =====================
print("\n--- Evaluation ---")

model.load_state_dict(torch.load("scheduler_model.pt", map_location=device, weights_only=True))
model.eval()

with torch.no_grad():
    t_val = torch.tensor(val_tasks, dtype=torch.float32).to(device)
    y_val = torch.tensor(val_labels, dtype=torch.long).to(device)
    scores = model(x, ei, t_val)
    preds = scores.argmax(dim=1)

    accuracy = (preds == y_val).float().mean().item()
    top3_acc = 0
    for i in range(len(val_tasks)):
        top3 = scores[i].topk(3).indices
        if y_val[i] in top3:
            top3_acc += 1
    top3_acc /= len(val_tasks)

print(f"  Top-1 Accuracy: {accuracy:.4f}")
print(f"  Top-3 Accuracy: {top3_acc:.4f}")

# =====================  COMPARISON WITH BASELINES  =====================
print("\n--- Baseline Comparison ---")

# Simple baseline implementations for Kaggle
def round_robin_schedule(tasks, n_machines):
    return [i % n_machines for i in range(len(tasks))]

def random_schedule(tasks, n_machines):
    return [random.randint(0, n_machines - 1) for _ in range(len(tasks))]

def first_fit_schedule(tasks, machine_feats, n_machines):
    assignments = []
    for t in tasks:
        best = 0
        for j in range(n_machines):
            if machine_feats[j, 0] * 16 * (1 - machine_feats[j, 2]) >= t[0]:
                best = j
                break
        assignments.append(best)
    return assignments

gnn_preds = preds.cpu().numpy()
rr_preds = round_robin_schedule(val_tasks, NUM_MACHINES)
rand_preds = random_schedule(val_tasks, NUM_MACHINES)
ff_preds = first_fit_schedule(val_tasks, machine_features, NUM_MACHINES)

def compute_metrics(predictions, tasks, machine_feats, labels):
    correct = sum(1 for p, l in zip(predictions, labels) if p == l)
    accuracy = correct / len(labels)

    exec_times = []
    for i, p in enumerate(predictions):
        cpu_cap = machine_feats[p, 0] * 16
        load = machine_feats[p, 2]
        cpu_req = tasks[i][0] * 4
        ratio = cpu_req / max(cpu_cap * (1 - load), 0.01)
        exec_times.append(ratio * 100 + random.uniform(5, 20))

    return {
        "accuracy": round(accuracy, 4),
        "avg_exec_time": round(np.mean(exec_times), 2),
        "std_exec_time": round(np.std(exec_times), 2),
    }

results = {
    "GNN Scheduler": compute_metrics(gnn_preds, val_tasks, machine_features, val_labels),
    "Round Robin": compute_metrics(rr_preds, val_tasks, machine_features, val_labels),
    "Random": compute_metrics(rand_preds, val_tasks, machine_features, val_labels),
    "First Fit": compute_metrics(ff_preds, val_tasks, machine_features, val_labels),
}

print(f"\n  {'Algorithm':<20} {'Accuracy':>10} {'Avg Exec Time':>15} {'Std':>10}")
print("  " + "-" * 58)
for name, m in results.items():
    print(f"  {name:<20} {m['accuracy']:>10.4f} {m['avg_exec_time']:>15.2f} {m['std_exec_time']:>10.2f}")

print("\n✅ Training pipeline complete!")
print("📁 Download 'scheduler_model.pt' and place it in: cloud_scheduler/model/scheduler_model.pt")
