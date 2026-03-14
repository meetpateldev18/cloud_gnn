import React from 'react';

export default function MetricsBar({ metrics }) {
  if (!metrics) return null;

  const items = [
    { label: 'Total Machines', value: metrics.total_machines },
    { label: 'Total Tasks Scheduled', value: metrics.total_tasks },
    { label: 'Avg Latency (ms)', value: metrics.avg_latency },
    { label: 'Avg Exec Time (ms)', value: metrics.avg_execution_time },
    { label: 'Avg CPU Utilization', value: `${(metrics.avg_cpu_utilization * 100).toFixed(1)}%` },
  ];

  return (
    <div className="metrics-row">
      {items.map((m) => (
        <div className="metric-card" key={m.label}>
          <div className="value">{m.value}</div>
          <div className="label">{m.label}</div>
        </div>
      ))}
    </div>
  );
}
