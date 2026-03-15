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
BORG_FILE   = "borg_traces_data.csv"   # Actual filename in dataset

# Try multiple possible Kaggle dataset paths (handles different dataset slugs)
_CANDIDATE_DIRS = [
    "/kaggle/input/google-2019-cluster-sample",
    "/kaggle/input/datasets/derrickmwiti/google-2019-cluster-sample",
    "/kaggle/input/google2019clustersample",
    "/kaggle/input/google-cluster-workload-traces",
]
DATASET_DIR = next(
    (d for d in _CANDIDATE_DIRS if os.path.isdir(d)),
    "/kaggle/input/google-2019-cluster-sample"  # fallback default
)

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

borg_path = os.path.join(DATASET_DIR, BORG_FILE)
borg_df = None

if os.path.isfile(borg_path):
    print(f"  Loaded: {borg_path}")
    borg_df = pd.read_csv(borg_path, nrows=500000)
    print(f"  Shape: {borg_df.shape}")
    print(f"  Columns: {list(borg_df.columns)}")
else:
    # Scan DATASET_DIR for any CSV
    if os.path.isdir(DATASET_DIR):
        for f in os.listdir(DATASET_DIR):
            if f.endswith('.csv'):
                borg_path = os.path.join(DATASET_DIR, f)
                print(f"  Found CSV in DATASET_DIR: {borg_path}")
                borg_df = pd.read_csv(borg_path, nrows=500000)
                print(f"  Shape: {borg_df.shape}")
                print(f"  Columns: {list(borg_df.columns)}")
                break

    # Last resort: walk ALL of /kaggle/input/ to find any CSV
    if borg_df is None and os.path.isdir("/kaggle/input"):
        print("  Searching all of /kaggle/input/ for a CSV...")
        for root, dirs, files in os.walk("/kaggle/input"):
            for fname in files:
                if fname.endswith('.csv'):
                    borg_path = os.path.join(root, fname)
                    print(f"  Found CSV: {borg_path}")
                    borg_df = pd.read_csv(borg_path, nrows=500000)
                    print(f"  Shape: {borg_df.shape}")
                    print(f"  Columns: {list(borg_df.columns)}")
                    break
            if borg_df is not None:
                break

    if borg_df is None:
        print("  [WARN] No CSV found in dataset dir – will use synthetic data")

# Parse borg_df into machine_df and task_df
machine_df = None
task_df = None

if borg_df is not None:
    cols = [c.lower().strip() for c in borg_df.columns]
    borg_df.columns = cols

    # ---- Detect CPU / memory columns ----
    # Prefer known good Borg column names; avoid string-encoded distributions
    _cpu_pref  = ['cycles_per_instruction', 'average_usage', 'maximum_usage',
                  'random_sample_usage', 'cpu_usage', 'cpu_request', 'cpu_cap']
    _mem_pref  = ['assigned_memory', 'page_cache_memory', 'memory_usage',
                  'mem_usage', 'memory_request', 'mem_request', 'memory_cap']

    cpu_col = next((c for c in _cpu_pref if c in cols), None)
    if cpu_col is None:
        # Generic fallback: any cpu-named col that isn't a distribution string
        cpu_col = next((c for c in cols if 'cpu' in c and 'distribution' not in c), None)

    mem_col = next((c for c in _mem_pref if c in cols), None)
    if mem_col is None:
        # Generic fallback: any memory col that isn't about instructions
        mem_col = next((c for c in cols if ('mem' in c or 'memory' in c) and 'instruction' not in c and 'distribution' not in c), None)

    machine_col = next((c for c in cols if c == 'machine_id' or (c != 'machine_id' and 'machine' in c)), None)
    prio_col    = next((c for c in cols if c == 'priority' or 'prio' in c), None)

    print(f"\n  Detected columns → cpu: {cpu_col}, mem: {mem_col}, machine: {machine_col}, priority: {prio_col}")

    # Convert to numeric
    for c in cols:
        borg_df[c] = pd.to_numeric(borg_df[c], errors='coerce')
    borg_df = borg_df.fillna(0)

    # Validate detected columns have non-zero values (guard against struct strings)
    if cpu_col and borg_df[cpu_col].max() == 0:
        print(f"  [WARN] {cpu_col} is all zeros after coerce — trying fallback")
        cpu_col = next((c for c in cols if borg_df[c].max() > 0 and 'cpu' in c and 'distribution' not in c), None)
        if cpu_col is None:
            cpu_col = next((c for c in cols if borg_df[c].max() > 0 and c not in ('time', 'collection_id', 'machine_id', 'priority', 'alloc_collection_id', 'instance_index')), None)
        print(f"  [WARN] Fell back to cpu_col: {cpu_col}")

    if mem_col and borg_df[mem_col].max() == 0:
        print(f"  [WARN] {mem_col} is all zeros after coerce — trying fallback")
        mem_col = next((c for c in cols if borg_df[c].max() > 0 and ('mem' in c or 'memory' in c) and 'instruction' not in c), None)
        if mem_col is None:
            mem_col = next((c for c in cols if borg_df[c].max() > 0 and c not in ('time', 'collection_id', 'machine_id', 'priority', 'alloc_collection_id', 'instance_index', cpu_col)), None)
        print(f"  [WARN] Fell back to mem_col: {mem_col}")

    # ---- Build machine_df ----
    if machine_col and cpu_col and mem_col:
        machine_df = (
            borg_df[[machine_col, cpu_col, mem_col]]
            .drop_duplicates(subset=[machine_col])
            .rename(columns={machine_col: "machine_id", cpu_col: "cpu_capacity", mem_col: "memory_capacity"})
        )
    else:
        # Use first two numeric columns as cpu/mem proxies
        num_cols = [c for c in cols if borg_df[c].dtype in [np.float64, np.float32, np.int64, np.int32]]
        if len(num_cols) >= 2:
            machine_df = pd.DataFrame({
                "machine_id": [f"machine_{i}" for i in range(NUM_MACHINES)],
                "cpu_capacity": np.random.uniform(2, 16, NUM_MACHINES),
                "memory_capacity": np.random.uniform(4, 64, NUM_MACHINES),
            })

    # ---- Build task_df ----
    if cpu_col and mem_col:
        task_df = borg_df.rename(columns={
            cpu_col: "cpu_request",
            mem_col: "memory_request",
        })
        if prio_col:
            task_df = task_df.rename(columns={prio_col: "priority"})
        else:
            task_df["priority"] = 0
        if machine_col:
            task_df = task_df.rename(columns={machine_col: "machine_id"})
        task_df = task_df[["cpu_request", "memory_request", "priority"]].copy()

# =====================  SYNTHETIC FALLBACK  =====================
if machine_df is None:
    print("\n--- Generating Synthetic Machine Data ---")
    machine_df = pd.DataFrame({
        "machine_id": [f"machine_{i}" for i in range(NUM_MACHINES)],
        "cpu_capacity": np.random.uniform(2, 16, NUM_MACHINES),
        "memory_capacity": np.random.uniform(4, 64, NUM_MACHINES),
    })

if task_df is None:
    print("--- Generating Synthetic Task Data ---")
    n_tasks = 20000
    task_df = pd.DataFrame({
        "cpu_request": np.random.uniform(0.05, 0.8, n_tasks),   # normalised 0-1
        "memory_request": np.random.uniform(0.05, 0.9, n_tasks),
        "priority": np.random.randint(0, 10, n_tasks),
    })

# =====================  FEATURE ENGINEERING  =====================
print("\n--- Feature Engineering ---")

# Ensure numeric types
for col in ["cpu_capacity", "memory_capacity"]:
    if col in machine_df.columns:
        machine_df[col] = pd.to_numeric(machine_df[col], errors="coerce")

for col in ["cpu_request", "memory_request", "priority"]:
    if col in task_df.columns:
        task_df[col] = pd.to_numeric(task_df[col], errors="coerce")

machine_df = machine_df.fillna(0)
task_df = task_df.fillna(0)

# Get unique machines — ensure exactly NUM_MACHINES with diverse capacities
raw_machines = machine_df.head(NUM_MACHINES) if "cpu_capacity" in machine_df.columns else pd.DataFrame()

machine_features = np.zeros((NUM_MACHINES, 4), dtype=np.float32)
for i in range(NUM_MACHINES):
    if i < len(raw_machines):
        row = raw_machines.iloc[i]
        cpu = float(row.get("cpu_capacity", 0))
        mem = float(row.get("memory_capacity", 0))
        # If values are near 0 or identical (normalised in source), spread them
        machine_features[i, 0] = cpu if cpu > 0.001 else (2.0 + i * 0.7)
        machine_features[i, 1] = mem if mem > 0.001 else (4.0 + i * 3.0)
    else:
        machine_features[i, 0] = 2.0 + i * 0.7
        machine_features[i, 1] = 4.0 + i * 3.0
    # Spread load so different machines are attractive for different tasks
    machine_features[i, 2] = 0.05 + (i % 5) * 0.12   # current_load: 0.05-0.53
    machine_features[i, 3] = 1.0 + i * 0.45           # network_bandwidth

# Normalize features column-wise
for j in range(4):
    col_max = machine_features[:, j].max()
    if col_max > 0:
        machine_features[:, j] /= col_max

print(f"  Machine features shape: {machine_features.shape}")
print(f"  CPU range (normalised): {machine_features[:,0].min():.3f} – {machine_features[:,0].max():.3f}")

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

task_features_list = []
labels_list = []

n_samples = min(len(task_df), 20000)
sample_tasks = task_df.sample(n=n_samples, random_state=SEED).reset_index(drop=True)

for idx in range(n_samples):
    row = sample_tasks.iloc[idx]
    cpu_req = float(row.get("cpu_request", 0))
    mem_req = float(row.get("memory_request", 0))
    prio    = float(row.get("priority", 0))
    arrival = idx / n_samples

    # Clamp to [0,1] — some datasets are already normalised
    cpu_req = np.clip(cpu_req, 0.0, 1.0) if cpu_req <= 1.0 else cpu_req / (task_df["cpu_request"].max() + 1e-6)
    mem_req = np.clip(mem_req, 0.0, 1.0) if mem_req <= 1.0 else mem_req / (task_df["memory_request"].max() + 1e-6)
    prio_n  = prio / max(float(task_df["priority"].max()), 1.0)

    task_feat = [float(cpu_req), float(mem_req), float(prio_n), float(arrival)]
    task_features_list.append(task_feat)

    # ---- FIXED label generation: balanced capacity-fit score ----
    # Each machine gets a score based on how well it fits THIS specific task.
    # Adding task-specific noise ensures all 20 machines can "win" depending on task requirements.
    scores = []
    for j in range(NUM_MACHINES):
        cpu_avail  = machine_features[j, 0] * (1.0 - machine_features[j, 2])
        mem_avail  = machine_features[j, 1]
        bandwidth  = machine_features[j, 3]

        fit_cpu = cpu_avail - cpu_req          # positive = enough room
        fit_mem = mem_avail - mem_req

        if fit_cpu < 0 or fit_mem < 0:
            score = -10.0                       # hard penalty for infeasible
        else:
            # Prefer tightest feasible fit (Best-Fit style) for diversity
            score = -(fit_cpu + fit_mem) + bandwidth * 0.1
            # Add small per-task noise so model learns generalisation
            score += np.random.normal(0, 0.05)

        scores.append(score)
    labels_list.append(int(np.argmax(scores)))

task_features = np.array(task_features_list, dtype=np.float32)
labels = np.array(labels_list, dtype=np.int64)

# Final normalisation of task features
for j in range(task_features.shape[1]):
    col_max = np.abs(task_features[:, j]).max()
    if col_max > 0:
        task_features[:, j] /= col_max

label_counts = pd.Series(labels).value_counts()
print(f"  Task features shape: {task_features.shape}")
print(f"  Labels shape: {labels.shape}")
print(f"  Unique machines used as labels: {label_counts.shape[0]} / {NUM_MACHINES}")
print(f"  Label distribution (top 5):\n{label_counts.head()}")

# Warn if still imbalanced
if label_counts.shape[0] < NUM_MACHINES // 2:
    print("  [WARN] Labels still imbalanced — model may overfit. Consider increasing noise.")

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
