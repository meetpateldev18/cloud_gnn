"""Seed the database with sample machines for demo / development."""

from __future__ import annotations
import random
from sqlalchemy.orm import Session
from .models import Machine


SAMPLE_MACHINES = [
    {"machine_id": f"machine-{i:03d}", "cpu_capacity": round(random.uniform(2.0, 16.0), 1),
     "ram_capacity": round(random.uniform(4.0, 64.0), 1),
     "network_bandwidth": round(random.uniform(1.0, 10.0), 1),
     "current_load": round(random.uniform(0.0, 0.7), 2)}
    for i in range(1, 21)
]

# Make it deterministic for reproducibility
random.seed(42)
SAMPLE_MACHINES = [
    {"machine_id": f"machine-{i:03d}",
     "cpu_capacity": round(2.0 + (i * 0.7), 1),
     "ram_capacity": round(4.0 + (i * 3.0), 1),
     "network_bandwidth": round(1.0 + (i * 0.45), 2),
     "current_load": round(0.05 + (i % 5) * 0.12, 2)}
    for i in range(1, 21)
]


def seed_machines(db: Session) -> None:
    """Insert sample machines if table is empty."""
    existing = db.query(Machine).count()
    if existing > 0:
        return
    for m in SAMPLE_MACHINES:
        db.add(Machine(**m))
    db.commit()
    print(f"[SEED] Inserted {len(SAMPLE_MACHINES)} sample machines.")
