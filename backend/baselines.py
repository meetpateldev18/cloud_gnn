"""Baseline scheduling algorithms for comparison."""

from __future__ import annotations
import random
import time


class RoundRobinScheduler:
    """Assign tasks to machines in circular order."""

    def __init__(self):
        self._counter = 0

    def schedule(self, task: dict, machines: list[dict]) -> tuple[int, float]:
        start = time.perf_counter()
        idx = self._counter % len(machines)
        self._counter += 1
        latency = time.perf_counter() - start
        return idx, latency


class RandomScheduler:
    """Assign tasks to a random machine."""

    def schedule(self, task: dict, machines: list[dict]) -> tuple[int, float]:
        start = time.perf_counter()
        idx = random.randint(0, len(machines) - 1)
        latency = time.perf_counter() - start
        return idx, latency


class FirstFitScheduler:
    """Assign task to the first machine with enough capacity."""

    def schedule(self, task: dict, machines: list[dict]) -> tuple[int, float]:
        start = time.perf_counter()
        for i, m in enumerate(machines):
            remaining_cpu = m["cpu_capacity"] * (1 - m["current_load"])
            remaining_mem = m["ram_capacity"]
            if remaining_cpu >= task["cpu_required"] and remaining_mem >= task["memory_required"]:
                latency = time.perf_counter() - start
                return i, latency
        # Fallback to first machine
        latency = time.perf_counter() - start
        return 0, latency


# ---- Simulation helpers ----

def simulate_execution_time(task: dict, machine: dict) -> float:
    """Estimate execution time based on task/machine mismatch."""
    cpu_ratio = task["cpu_required"] / max(machine["cpu_capacity"], 0.01)
    load_penalty = 1 + machine["current_load"] * 2
    return round(cpu_ratio * load_penalty * 100 + random.uniform(5, 20), 2)


def compute_cpu_utilization(task: dict, machine: dict) -> float:
    """Estimate resulting CPU utilization after placing task."""
    added = task["cpu_required"] / max(machine["cpu_capacity"], 0.01)
    return round(min(machine["current_load"] + added, 1.0), 4)
