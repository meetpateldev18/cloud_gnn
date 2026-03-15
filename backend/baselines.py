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
    """Assign task to the first machine with enough available resources."""

    def schedule(self, task: dict, machines: list[dict]) -> tuple[int, float]:
        start = time.perf_counter()
        for i, m in enumerate(machines):
            if m["available_cpu"] >= task["cpu_request"] and m["available_ram"] >= task["memory_request"]:
                latency = time.perf_counter() - start
                return i, latency
        # Fallback to first machine if none strictly fit
        latency = time.perf_counter() - start
        return 0, latency


# ---- Simulation helpers ----

def simulate_execution_time(task: dict, machine: dict) -> float:
    """Estimate simulated execution time (ms) based on task/machine mismatch."""
    cpu_ratio = task["cpu_request"] / max(machine["total_cpu"], 0.01)
    load_penalty = 1 + machine["load"] * 2
    return round(cpu_ratio * load_penalty * 100 + random.uniform(5, 20), 2)


def compute_cpu_utilization(task: dict, machine: dict) -> float:
    """Estimate resulting CPU utilization after placing task."""
    added = task["cpu_request"] / max(machine["total_cpu"], 0.01)
    return round(min(machine["load"] + added, 1.0), 4)
