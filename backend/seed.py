"""Seed the database with sample machines for demo / development."""

from __future__ import annotations
from sqlalchemy.orm import Session
from .models import Machine

# Deterministic 20-machine cluster: capacity grows with machine number.
# Machines 5, 10, 15, 20 (end of each group of 5) start with lowest load (5%).
_BASE = [
    {
        "machine_id": f"machine-{i:03d}",
        "total_cpu": round(2.0 + (i * 0.7), 1),
        "total_ram": round(4.0 + (i * 3.0), 1),
        "bandwidth": round(1.0 + (i * 0.45), 2),
        "load": round(0.05 + (i % 5) * 0.12, 2),
    }
    for i in range(1, 21)
]

SAMPLE_MACHINES = []
for m in _BASE:
    m["available_cpu"] = round(m["total_cpu"] * (1.0 - m["load"]), 2)
    m["available_ram"] = round(m["total_ram"] * (1.0 - m["load"]), 2)
    SAMPLE_MACHINES.append(m)


def seed_machines(db: Session) -> None:
    """Insert sample machines if table is empty."""
    existing = db.query(Machine).count()
    if existing > 0:
        return
    for m in SAMPLE_MACHINES:
        db.add(Machine(**m))
    db.commit()
    print(f"[SEED] Inserted {len(SAMPLE_MACHINES)} sample machines.")
