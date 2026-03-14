"""Unit tests for the GNN scheduler module."""

import pytest
import numpy as np

# Test the heuristic fallback (no torch dependency needed)
from backend.scheduler import GNNScheduler

MACHINES = [
    {"machine_id": "m1", "cpu_capacity": 8.0, "ram_capacity": 32.0, "network_bandwidth": 5.0, "current_load": 0.2},
    {"machine_id": "m2", "cpu_capacity": 4.0, "ram_capacity": 16.0, "network_bandwidth": 3.0, "current_load": 0.8},
    {"machine_id": "m3", "cpu_capacity": 16.0, "ram_capacity": 64.0, "network_bandwidth": 10.0, "current_load": 0.1},
]

TASK = {"cpu_required": 2.0, "memory_required": 4.0, "priority": 1}


class TestHeuristicScheduler:
    def test_picks_best_machine(self):
        idx = GNNScheduler._heuristic_schedule(TASK, MACHINES)
        # m3 has most remaining capacity
        assert idx == 2

    def test_overloaded_avoidance(self):
        machines = [
            {"machine_id": "m1", "cpu_capacity": 4.0, "ram_capacity": 8.0, "network_bandwidth": 1.0, "current_load": 0.95},
            {"machine_id": "m2", "cpu_capacity": 8.0, "ram_capacity": 16.0, "network_bandwidth": 1.0, "current_load": 0.1},
        ]
        idx = GNNScheduler._heuristic_schedule(TASK, machines)
        assert idx == 1  # avoids overloaded m1


class TestGNNSchedulerInit:
    def test_no_model_file(self):
        sched = GNNScheduler(model_path="nonexistent.pt")
        assert sched.model is None

    def test_predict_without_model(self):
        sched = GNNScheduler(model_path="nonexistent.pt")
        idx = sched.predict(TASK, MACHINES)
        assert 0 <= idx < len(MACHINES)
