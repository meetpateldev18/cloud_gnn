"""SQLAlchemy ORM models for the cloud scheduler database."""

from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey
from sqlalchemy.sql import func

from .database import Base


class Machine(Base):
    __tablename__ = "machines"

    machine_id = Column(String(64), primary_key=True)
    total_cpu = Column(Float, nullable=False)       # Total CPU cores
    total_ram = Column(Float, nullable=False)       # Total RAM in GB
    available_cpu = Column(Float, nullable=False)  # Currently free CPU cores
    available_ram = Column(Float, nullable=False)  # Currently free RAM in GB
    bandwidth = Column(Float, nullable=False, default=1.0)  # Network bandwidth Gbps
    load = Column(Float, nullable=False, default=0.0)       # 0.0 – 1.0 fraction


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    cpu_request = Column(Float, nullable=False)
    memory_request = Column(Float, nullable=False)
    priority = Column(Integer, nullable=False, default=0)
    assigned_machine_id = Column(String(64), ForeignKey("machines.machine_id"), nullable=True)
    arrival_time = Column(DateTime, server_default=func.now())
    start_time = Column(DateTime, nullable=True)
    execution_duration = Column(Float, nullable=True)  # seconds (5 – 20)
    status = Column(String(32), default="running")     # running | completed | queued
    waiting_time = Column(Float, nullable=True)        # seconds from arrival to start


class SchedulingResult(Base):
    __tablename__ = "scheduling_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False)
    machine_id = Column(String(64), ForeignKey("machines.machine_id"), nullable=False)
    algorithm = Column(String(32), nullable=False, default="gnn")
    latency = Column(Float)        # scheduling decision time in ms
    execution_time = Column(Float) # simulated execution time in ms


class SchedulerComparison(Base):
    __tablename__ = "scheduler_comparison"

    id = Column(Integer, primary_key=True, autoincrement=True)
    algorithm = Column(String(32), nullable=False)
    average_latency = Column(Float)
    execution_time = Column(Float)
    cpu_utilization = Column(Float)
    evaluated_at = Column(DateTime, server_default=func.now())
