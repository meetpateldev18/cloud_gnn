"""
FastAPI main application – GNN Cloud Task Scheduler
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import init_db, SessionLocal
from .seed import seed_machines
from .routes import scheduling, machines


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: create tables and seed data."""
    init_db()
    db = SessionLocal()
    try:
        seed_machines(db)
    finally:
        db.close()
    yield


app = FastAPI(
    title="GNN Cloud Task Scheduler",
    description="Graph Neural Network-based task scheduling for distributed cloud systems",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS – allow frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(scheduling.router, tags=["Scheduling"])
app.include_router(machines.router, tags=["Machines & Metrics"])


@app.get("/health")
def health():
    return {"status": "ok", "service": "gnn-cloud-scheduler"}
