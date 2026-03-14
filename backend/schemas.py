"""Pydantic schemas for request / response validation."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel


# ---- Machine ----
class MachineOut(BaseModel):
    machine_id: str
    cpu_capacity: float
    ram_capacity: float
    network_bandwidth: float
    current_load: float

    class Config:
        from_attributes = True


# ---- Task ----
class TaskIn(BaseModel):
    cpu_required: float
    memory_required: float
    priority: int = 0


class TaskOut(BaseModel):
    task_id: int
    cpu_required: float
    memory_required: float
    priority: int
    arrival_time: Optional[datetime] = None

    class Config:
        from_attributes = True


# ---- Scheduling ----
class ScheduleRequest(BaseModel):
    cpu_required: float
    memory_required: float
    priority: int = 0


class ScheduleResponse(BaseModel):
    task_id: int
    assigned_machine: str
    algorithm: str
    latency: float
    execution_time: float


# ---- Comparison ----
class ComparisonRow(BaseModel):
    algorithm: str
    average_latency: float
    execution_time: float
    cpu_utilization: float

    class Config:
        from_attributes = True


# ---- Metrics ----
class MetricsOut(BaseModel):
    total_tasks: int
    total_machines: int
    avg_latency: float
    avg_execution_time: float
    avg_cpu_utilization: float
