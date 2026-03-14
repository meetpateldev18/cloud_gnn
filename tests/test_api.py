"""Integration tests for the FastAPI application."""

import pytest
from fastapi.testclient import TestClient

# Use SQLite in-memory for testing
import backend.database as db_mod
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

TEST_DB_URL = "sqlite:///./test_scheduler.db"
test_engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestSession = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

# Patch database before importing app
db_mod.engine = test_engine
db_mod.SessionLocal = TestSession


def override_get_db():
    db = TestSession()
    try:
        yield db
    finally:
        db.close()


from backend.main import app
from backend.database import get_db, Base
from backend.seed import seed_machines

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=test_engine)
    db = TestSession()
    seed_machines(db)
    db.close()
    yield
    Base.metadata.drop_all(bind=test_engine)


class TestHealthEndpoint:
    def test_health(self):
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"


class TestMachinesEndpoint:
    def test_list_machines(self):
        r = client.get("/machines")
        assert r.status_code == 200
        data = r.json()
        assert len(data) == 20

    def test_machine_fields(self):
        r = client.get("/machines")
        m = r.json()[0]
        assert "machine_id" in m
        assert "cpu_capacity" in m
        assert "ram_capacity" in m


class TestScheduleEndpoint:
    def test_schedule_task(self):
        r = client.post("/schedule_task", json={
            "cpu_required": 2.0,
            "memory_required": 4.0,
            "priority": 1,
        })
        assert r.status_code == 200
        data = r.json()
        assert "assigned_machine" in data
        assert "latency" in data
        assert data["algorithm"] == "gnn"

    def test_schedule_updates_metrics(self):
        client.post("/schedule_task", json={"cpu_required": 1.0, "memory_required": 2.0, "priority": 0})
        r = client.get("/metrics")
        assert r.status_code == 200
        assert r.json()["total_tasks"] >= 1


class TestComparisonEndpoint:
    def test_comparison_returns_data(self):
        # Schedule a task first to generate comparison data
        client.post("/schedule_task", json={"cpu_required": 1.0, "memory_required": 2.0, "priority": 0})
        r = client.get("/comparison")
        assert r.status_code == 200
        data = r.json()
        assert len(data) >= 1
        algos = {d["algorithm"] for d in data}
        assert "gnn" in algos


class TestGraphEndpoint:
    def test_graph_structure(self):
        r = client.get("/graph")
        assert r.status_code == 200
        data = r.json()
        assert "nodes" in data
        assert "edges" in data
        assert len(data["nodes"]) == 20
