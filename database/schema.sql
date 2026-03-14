-- ============================================================
-- Database: cloud_scheduler
-- PostgreSQL schema for GNN Task Scheduling System
-- ============================================================

-- Create database (run once, outside transaction)
-- CREATE DATABASE cloud_scheduler;

-- Connect to cloud_scheduler before running the rest.

-- ----- machines -----
CREATE TABLE IF NOT EXISTS machines (
    machine_id   VARCHAR(64) PRIMARY KEY,
    cpu_capacity FLOAT       NOT NULL,
    ram_capacity FLOAT       NOT NULL,
    network_bandwidth FLOAT  NOT NULL DEFAULT 1.0,
    current_load FLOAT       NOT NULL DEFAULT 0.0
);

-- ----- tasks -----
CREATE TABLE IF NOT EXISTS tasks (
    task_id        SERIAL PRIMARY KEY,
    cpu_required   FLOAT   NOT NULL,
    memory_required FLOAT  NOT NULL,
    priority       INT     NOT NULL DEFAULT 0,
    arrival_time   TIMESTAMP NOT NULL DEFAULT NOW()
);

-- ----- scheduling_results -----
CREATE TABLE IF NOT EXISTS scheduling_results (
    id              SERIAL PRIMARY KEY,
    task_id         INT        NOT NULL REFERENCES tasks(task_id),
    machine_id      VARCHAR(64) NOT NULL REFERENCES machines(machine_id),
    algorithm       VARCHAR(32) NOT NULL DEFAULT 'gnn',
    latency         FLOAT,
    execution_time  FLOAT,
    scheduled_at    TIMESTAMP NOT NULL DEFAULT NOW()
);

-- ----- scheduler_comparison -----
CREATE TABLE IF NOT EXISTS scheduler_comparison (
    id              SERIAL PRIMARY KEY,
    algorithm       VARCHAR(32) NOT NULL,
    average_latency FLOAT,
    execution_time  FLOAT,
    cpu_utilization FLOAT,
    evaluated_at    TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_sched_results_task ON scheduling_results(task_id);
CREATE INDEX IF NOT EXISTS idx_sched_results_machine ON scheduling_results(machine_id);
CREATE INDEX IF NOT EXISTS idx_sched_comparison_algo ON scheduler_comparison(algorithm);
