import React from 'react';

export default function MetricsBar({ metrics }) {
  if (!metrics) return null;

  const items = [
    { label: 'Total Machines',         value: metrics.total_machines },
    { label: 'Total Tasks',            value: metrics.total_tasks },
    { label: 'Running Tasks',          value: metrics.running_tasks,    color: '#fbbf24' },
    { label: 'Completed Tasks',        value: metrics.completed_tasks,  color: '#4ade80' },
    { label: 'Avg GNN Latency',        value: `${metrics.avg_latency} ms` },
    { label: 'Avg Completion Time',    value: `${metrics.avg_completion_time}s` },
    { label: 'Avg Waiting Time',       value: `${(metrics.avg_waiting_time * 1000).toFixed(1)} ms` },
    { label: 'Avg CPU Utilization',    value: `${(metrics.avg_cpu_utilization * 100).toFixed(1)}%` },
    { label: 'Cluster Throughput',     value: `${metrics.cluster_throughput}/min` },
  ];

  return (
    <div className="metrics-row">
      {items.map((m) => (
        <div className="metric-card" key={m.label}>
          <div className="value" style={m.color ? { color: m.color } : {}}>{m.value}</div>
          <div className="label">{m.label}</div>
        </div>
      ))}
    </div>
  );
}
