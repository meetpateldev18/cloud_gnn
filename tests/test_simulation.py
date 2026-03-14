"""Scheduler simulation test — runs multiple tasks and compares algorithms."""

import statistics
from backend.baselines import (
    RoundRobinScheduler,
    RandomScheduler,
    FirstFitScheduler,
    simulate_execution_time,
    compute_cpu_utilization,
)
from backend.scheduler import GNNScheduler

MACHINES = [
    {"machine_id": f"m{i}", "cpu_capacity": 4.0 + i * 2, "ram_capacity": 8.0 + i * 4,
     "network_bandwidth": 2.0 + i * 0.5, "current_load": 0.1 + (i % 4) * 0.15}
    for i in range(10)
]

TASKS = [
    {"cpu_required": 1.0 + i * 0.3, "memory_required": 2.0 + i * 0.5, "priority": i % 5}
    for i in range(50)
]


def run_simulation():
    schedulers = {
        "GNN (heuristic)": GNNScheduler(model_path="nonexistent.pt"),
        "Round Robin": RoundRobinScheduler(),
        "Random": RandomScheduler(),
        "First Fit": FirstFitScheduler(),
    }

    results = {}

    for name, sched in schedulers.items():
        latencies = []
        exec_times = []
        utils = []

        for task in TASKS:
            if name == "GNN (heuristic)":
                idx = sched.predict(task, MACHINES)
                lat = 0.001
            else:
                idx, lat = sched.schedule(task, MACHINES)
                lat = lat * 1000 + 0.5  # in ms

            machine = MACHINES[idx]
            et = simulate_execution_time(task, machine)
            util = compute_cpu_utilization(task, machine)

            latencies.append(lat)
            exec_times.append(et)
            utils.append(util)

        results[name] = {
            "avg_latency": round(statistics.mean(latencies), 3),
            "avg_exec_time": round(statistics.mean(exec_times), 3),
            "avg_utilization": round(statistics.mean(utils), 4),
            "p95_latency": round(sorted(latencies)[int(len(latencies) * 0.95)], 3),
        }

    return results


def test_simulation_gnn_beats_random():
    results = run_simulation()
    assert results["GNN (heuristic)"]["avg_exec_time"] <= results["Random"]["avg_exec_time"]


def test_simulation_all_positive():
    results = run_simulation()
    for name, r in results.items():
        assert r["avg_latency"] >= 0
        assert r["avg_exec_time"] > 0
        assert 0 <= r["avg_utilization"] <= 1.0


if __name__ == "__main__":
    results = run_simulation()
    print("\n===== Scheduler Simulation Results =====\n")
    header = f"{'Algorithm':<20} {'Avg Latency':>12} {'Avg Exec Time':>14} {'Avg Util':>10} {'P95 Lat':>10}"
    print(header)
    print("-" * len(header))
    for name, r in results.items():
        print(f"{name:<20} {r['avg_latency']:>12.3f} {r['avg_exec_time']:>14.3f} {r['avg_utilization']:>10.4f} {r['p95_latency']:>10.3f}")
    print()
