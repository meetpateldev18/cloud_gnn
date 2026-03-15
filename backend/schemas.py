"""Pydantic schemas for request / response validation."""

from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel


# ---- Machine ----
class MachineOut(BaseModel):
    machine_id: str
    total_cpu: float
    total_ram: float
    available_cpu: float
    available_ram: float
    bandwidth: float
    load: float

    class Config:
        from_attributes = True


# ---- Task ----
class TaskOut(BaseModel):
    id: int
    cpu_request: float
    memory_request: float
    priority: int
    assigned_machine_id: Optional[str] = None
    arrival_time: Optional[datetime] = None
    start_time: Optional[datetime] = None
    execution_duration: Optional[float] = None
    status: str
    waiting_time: Optional[float] = None

    class Config:
        from_attributes = True


# ---- Scheduling ----
class ScheduleRequest(BaseModel):
    cpu_required: float    # kept for frontend backward-compatibility
    memory_required: float
    priority: int = 0


class ScheduleResponse(BaseModel):
    task_id: int
    assigned_machine: str
    algorithm: str
    latency: float
    execution_time: float
    execution_duration: float
    status: str
    comparison: Optional[Dict[str, Any]] = None


# ---- Comparison ----
class ComparisonRow(BaseModel):
    algorithm: str
    average_latency: float
    execution_time: float
    cpu_utilization: float
    avg_completion_time: float = 0.0   # real seconds (from task lifecycle)
    avg_waiting_time: float = 0.0      # real seconds
    throughput: float = 0.0            # tasks per minute

    class Config:
        from_attributes = True


# ---- Metrics ----
class MetricsOut(BaseModel):
    total_tasks: int
    total_machines: int
    running_tasks: int
    completed_tasks: int
    avg_latency: float
    avg_execution_time: float
    avg_cpu_utilization: float
    avg_waiting_time: float
    avg_completion_time: float
    cluster_throughput: float
