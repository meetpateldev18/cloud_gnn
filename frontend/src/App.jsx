import React, { useState, useEffect, useCallback } from 'react';
import MetricsBar from './components/MetricsBar';
import GraphView from './components/GraphView';
import TaskForm from './components/TaskForm';
import ComparisonSection from './components/ComparisonSection';
import MachineTable from './components/MachineTable';
import TaskList from './components/TaskList';
import { getMetrics, getComparison, getMachines, getGraph, getHealth, getTasks } from './api';

export default function App() {
  const [metrics, setMetrics]       = useState(null);
  const [comparison, setComparison] = useState([]);
  const [machines, setMachines]     = useState([]);
  const [graphData, setGraphData]   = useState({ nodes: [], edges: [] });
  const [healthy, setHealthy]       = useState(null);
  const [lastResult, setLastResult] = useState(null);
  const [tasks, setTasks]           = useState([]);

  const refresh = useCallback(async () => {
    try {
      const [mRes, metRes, compRes, gRes, hRes, tRes] = await Promise.all([
        getMachines(),
        getMetrics(),
        getComparison(),
        getGraph(),
        getHealth(),
        getTasks(),
      ]);
      setMachines(mRes.data);
      setMetrics(metRes.data);
      setComparison(compRes.data);
      setGraphData(gRes.data);
      setHealthy(hRes.data.status === 'ok');
      setTasks(tRes.data);
    } catch {
      setHealthy(false);
    }
  }, []);

  useEffect(() => {
    refresh();
    // Auto-refresh every 3 seconds to show task completions & resource updates
    const id = setInterval(refresh, 3000);
    return () => clearInterval(id);
  }, [refresh]);

  return (
    <div className="app">
      <header className="header">
        <h1>GNN Cloud Task Scheduler</h1>
        <p>
          Graph Neural Network-based task scheduling for distributed cloud systems
          {healthy !== null && (
            <span style={{ marginLeft: 12 }}>
              — API{' '}
              <span className={healthy ? 'status-ok' : 'status-err'}>
                {healthy ? '● Connected' : '● Disconnected'}
              </span>
            </span>
          )}
        </p>
      </header>

      {/* KPI Metrics */}
      <MetricsBar metrics={metrics} />

      {/* Main Grid */}
      <div className="grid-2">
        {/* Left: Graph + Machines */}
        <div>
          <div className="card">
            <h2>☁ Cloud Infrastructure Graph</h2>
            <GraphView data={graphData} />
          </div>
          <MachineTable machines={machines} />
        </div>

        {/* Right: Task Submission + Result */}
        <div>
          <TaskForm onResult={(r) => { setLastResult(r); refresh(); }} />
          {lastResult && (
            <div className="card">
              <h2>🤖 AI Scheduling Result</h2>
              {lastResult.status === 'queued' ? (
                <div className="result-box" style={{ borderColor: '#fbbf24' }}>
                  <div className="machine-name" style={{ color: '#fbbf24' }}>⏳ Task Queued</div>
                  <div className="details">{lastResult.message}</div>
                </div>
              ) : (
                <>
                  <div className="result-box">
                    <div className="machine-name">{lastResult.assigned_machine}</div>
                    <div className="details">
                      GNN Latency: <strong>{lastResult.latency} ms</strong>
                      &nbsp;|&nbsp;
                      Exec Time: <strong>{lastResult.execution_time} ms</strong>
                      &nbsp;|&nbsp;
                      Duration: <strong>{lastResult.execution_duration}s</strong>
                      <span style={{
                        marginLeft: 10,
                        padding: '2px 8px',
                        background: '#22c55e22',
                        color: '#4ade80',
                        borderRadius: 4,
                        fontSize: '0.8rem',
                      }}>
                        ● {lastResult.status}
                      </span>
                    </div>
                  </div>
                  {lastResult.comparison && (
                    <table className="comparison-table" style={{ marginTop: 12 }}>
                      <thead>
                        <tr>
                          <th>Algorithm</th>
                          <th>Machine</th>
                          <th>Latency (ms)</th>
                          <th>Exec (ms)</th>
                        </tr>
                      </thead>
                      <tbody>
                        {Object.entries(lastResult.comparison).map(([name, v]) => (
                          <tr key={name}>
                            <td style={{ textTransform: 'capitalize' }}>{name.replace('_', ' ')}</td>
                            <td>{v.machine_id}</td>
                            <td>{v.latency}</td>
                            <td>{v.execution_time}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  )}
                </>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Live Task List */}
      <TaskList tasks={tasks} />

      {/* Comparison Section */}
      <ComparisonSection comparison={comparison} />
    </div>
  );
}
