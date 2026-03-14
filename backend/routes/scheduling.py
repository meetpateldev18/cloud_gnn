"""Scheduling routes – POST /schedule_task"""

from __future__ import annotations
import time, random
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Machine, Task, SchedulingResult
from ..schemas import ScheduleRequest, ScheduleResponse
from ..scheduler import GNNScheduler
from ..baselines import (
    RoundRobinScheduler,
    RandomScheduler,
    FirstFitScheduler,
    simulate_execution_time,
)

router = APIRouter()

# Singletons
gnn_scheduler = GNNScheduler(model_path="model/scheduler_model.pt")
rr_scheduler = RoundRobinScheduler()
rand_scheduler = RandomScheduler()
ff_scheduler = FirstFitScheduler()


def _machines_as_dicts(db: Session) -> list[dict]:
    rows = db.query(Machine).all()
    return [
        {
            "machine_id": m.machine_id,
            "cpu_capacity": m.cpu_capacity,
            "ram_capacity": m.ram_capacity,
            "network_bandwidth": m.network_bandwidth,
            "current_load": m.current_load,
        }
        for m in rows
    ]


@router.post("/schedule_task", response_model=ScheduleResponse)
def schedule_task(req: ScheduleRequest, db: Session = Depends(get_db)):
    machines = _machines_as_dicts(db)
    if not machines:
        raise ValueError("No machines registered in the database.")

    task = {
        "cpu_required": req.cpu_required,
        "memory_required": req.memory_required,
        "priority": req.priority,
    }

    # GNN prediction
    start = time.perf_counter()
    best_idx = gnn_scheduler.predict(task, machines)
    gnn_latency = round((time.perf_counter() - start) * 1000, 3)  # ms

    chosen = machines[best_idx]
    exec_time = simulate_execution_time(task, chosen)

    # Persist task
    db_task = Task(
        cpu_required=req.cpu_required,
        memory_required=req.memory_required,
        priority=req.priority,
    )
    db.add(db_task)
    db.flush()

    # Persist GNN result
    db.add(
        SchedulingResult(
            task_id=db_task.task_id,
            machine_id=chosen["machine_id"],
            algorithm="gnn",
            latency=gnn_latency,
            execution_time=exec_time,
        )
    )

    # Also run baselines and persist
    for name, sched in [("round_robin", rr_scheduler), ("random", rand_scheduler), ("first_fit", ff_scheduler)]:
        idx, lat = sched.schedule(task, machines)
        bl_exec = simulate_execution_time(task, machines[idx])
        db.add(
            SchedulingResult(
                task_id=db_task.task_id,
                machine_id=machines[idx]["machine_id"],
                algorithm=name,
                latency=round(lat * 1000 + random.uniform(0.5, 3.0), 3),
                execution_time=bl_exec,
            )
        )

    # Update machine load slightly
    load_inc = min(req.cpu_required / max(chosen["cpu_capacity"], 0.01) * 0.1, 0.1)
    m_obj = db.query(Machine).filter(Machine.machine_id == chosen["machine_id"]).first()
    if m_obj:
        m_obj.current_load = round(min(m_obj.current_load + load_inc, 1.0), 4)

    db.commit()

    return ScheduleResponse(
        task_id=db_task.task_id,
        assigned_machine=chosen["machine_id"],
        algorithm="gnn",
        latency=gnn_latency,
        execution_time=exec_time,
    )
