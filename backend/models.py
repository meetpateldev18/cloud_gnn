"""SQLAlchemy ORM models for the cloud scheduler database."""

from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey
from sqlalchemy.sql import func

from .database import Base


class Machine(Base):
    __tablename__ = "machines"

    machine_id = Column(String(64), primary_key=True)
    cpu_capacity = Column(Float, nullable=False)
    ram_capacity = Column(Float, nullable=False)
    network_bandwidth = Column(Float, nullable=False, default=1.0)
    current_load = Column(Float, nullable=False, default=0.0)


class Task(Base):
    __tablename__ = "tasks"

    task_id = Column(Integer, primary_key=True, autoincrement=True)
    cpu_required = Column(Float, nullable=False)
    memory_required = Column(Float, nullable=False)
    priority = Column(Integer, nullable=False, default=0)
    arrival_time = Column(DateTime, server_default=func.now())


class SchedulingResult(Base):
    __tablename__ = "scheduling_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(Integer, ForeignKey("tasks.task_id"), nullable=False)
    machine_id = Column(String(64), ForeignKey("machines.machine_id"), nullable=False)
    algorithm = Column(String(32), nullable=False, default="gnn")
    latency = Column(Float)
    execution_time = Column(Float)
    scheduled_at = Column(DateTime, server_default=func.now())


class SchedulerComparison(Base):
    __tablename__ = "scheduler_comparison"

    id = Column(Integer, primary_key=True, autoincrement=True)
    algorithm = Column(String(32), nullable=False)
    average_latency = Column(Float)
    execution_time = Column(Float)
    cpu_utilization = Column(Float)
    evaluated_at = Column(DateTime, server_default=func.now())
