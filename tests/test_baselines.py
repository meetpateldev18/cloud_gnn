"""Unit tests for baseline scheduler algorithms."""

import pytest
from backend.baselines import (
    RoundRobinScheduler,
    RandomScheduler,
    FirstFitScheduler,
    simulate_execution_time,
    compute_cpu_utilization,
)

MACHINES = [
    {"machine_id": "m1", "cpu_capacity": 8.0, "ram_capacity": 32.0, "network_bandwidth": 5.0, "current_load": 0.2},
    {"machine_id": "m2", "cpu_capacity": 4.0, "ram_capacity": 16.0, "network_bandwidth": 3.0, "current_load": 0.5},
    {"machine_id": "m3", "cpu_capacity": 16.0, "ram_capacity": 64.0, "network_bandwidth": 10.0, "current_load": 0.1},
]

TASK = {"cpu_required": 2.0, "memory_required": 4.0, "priority": 1}


class TestRoundRobin:
    def test_cycles_through_machines(self):
        sched = RoundRobinScheduler()
        indices = [sched.schedule(TASK, MACHINES)[0] for _ in range(6)]
        assert indices == [0, 1, 2, 0, 1, 2]

    def test_returns_latency(self):
        sched = RoundRobinScheduler()
        _, latency = sched.schedule(TASK, MACHINES)
        assert latency >= 0


class TestRandomScheduler:
    def test_valid_index(self):
        sched = RandomScheduler()
        for _ in range(20):
            idx, _ = sched.schedule(TASK, MACHINES)
            assert 0 <= idx < len(MACHINES)


class TestFirstFit:
    def test_picks_first_capable(self):
        sched = FirstFitScheduler()
        idx, _ = sched.schedule(TASK, MACHINES)
        assert idx == 0  # m1 has enough capacity

    def test_large_task_fallback(self):
        big_task = {"cpu_required": 100.0, "memory_required": 200.0, "priority": 5}
        sched = FirstFitScheduler()
        idx, _ = sched.schedule(big_task, MACHINES)
        assert idx == 0  # fallback


class TestSimulation:
    def test_execution_time_positive(self):
        et = simulate_execution_time(TASK, MACHINES[0])
        assert et > 0

    def test_cpu_utilization_bounded(self):
        util = compute_cpu_utilization(TASK, MACHINES[0])
        assert 0 <= util <= 1.0
