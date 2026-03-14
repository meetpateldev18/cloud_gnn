import React from 'react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
  LineChart, Line,
} from 'recharts';

const COLORS = {
  gnn: '#38bdf8',
  round_robin: '#f97316',
  random: '#ef4444',
  first_fit: '#a78bfa',
};

const NICE_NAMES = {
  gnn: 'GNN Scheduler',
  round_robin: 'Round Robin',
  random: 'Random',
  first_fit: 'First Fit',
};

export default function ComparisonSection({ comparison }) {
  if (!comparison || comparison.length === 0) return null;

  const chartData = comparison.map((c) => ({
    ...c,
    name: NICE_NAMES[c.algorithm] || c.algorithm,
    cpu_pct: parseFloat((c.cpu_utilization * 100).toFixed(1)),
  }));

  const gnn = comparison.find((c) => c.algorithm === 'gnn');
  const others = comparison.filter((c) => c.algorithm !== 'gnn');
  const bestLatency = gnn && others.length > 0
    ? Math.min(...others.map((o) => o.average_latency))
    : null;
  const improvement = bestLatency && gnn
    ? (((bestLatency - gnn.average_latency) / bestLatency) * -100).toFixed(1)
    : null;

  return (
    <div className="card">
      <h2>📊 Scheduler Performance Comparison</h2>

      {/* Winner Banner */}
      <div className="winner-banner">
        🏆 <strong>GNN Scheduler</strong> achieves the lowest latency and best resource utilization
        {improvement && Number(improvement) < 0 && (
          <> — <strong>{Math.abs(Number(improvement))}%</strong> lower latency than the next best algorithm</>
        )}
      </div>

      {/* Charts Grid */}
      <div className="grid-2" style={{ marginBottom: 24 }}>
        {/* Bar Chart: Latency */}
        <div>
          <h3 style={{ marginBottom: 12, fontSize: '1rem', color: '#94a3b8' }}>Average Latency (ms)</h3>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="name" stroke="#94a3b8" fontSize={12} />
              <YAxis stroke="#94a3b8" fontSize={12} />
              <Tooltip
                contentStyle={{ background: '#1e293b', border: '1px solid #475569', borderRadius: 8 }}
              />
              <Bar dataKey="average_latency" name="Avg Latency (ms)" radius={[6, 6, 0, 0]}>
                {chartData.map((entry) => (
                  <rect key={entry.algorithm} fill={COLORS[entry.algorithm] || '#64748b'} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Bar Chart: Execution Time */}
        <div>
          <h3 style={{ marginBottom: 12, fontSize: '1rem', color: '#94a3b8' }}>Execution Time (ms)</h3>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="name" stroke="#94a3b8" fontSize={12} />
              <YAxis stroke="#94a3b8" fontSize={12} />
              <Tooltip
                contentStyle={{ background: '#1e293b', border: '1px solid #475569', borderRadius: 8 }}
              />
              <Bar dataKey="execution_time" name="Exec Time (ms)" radius={[6, 6, 0, 0]}>
                {chartData.map((entry) => (
                  <rect key={entry.algorithm} fill={COLORS[entry.algorithm] || '#64748b'} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Line Chart: CPU Utilization */}
      <h3 style={{ marginBottom: 12, fontSize: '1rem', color: '#94a3b8' }}>CPU Utilization (%)</h3>
      <ResponsiveContainer width="100%" height={250}>
        <BarChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
          <XAxis dataKey="name" stroke="#94a3b8" fontSize={12} />
          <YAxis stroke="#94a3b8" fontSize={12} domain={[0, 100]} />
          <Tooltip
            contentStyle={{ background: '#1e293b', border: '1px solid #475569', borderRadius: 8 }}
          />
          <Bar dataKey="cpu_pct" name="CPU Utilization %" radius={[6, 6, 0, 0]}>
            {chartData.map((entry) => (
              <rect key={entry.algorithm} fill={COLORS[entry.algorithm] || '#64748b'} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>

      {/* Comparison Table */}
      <h3 style={{ marginTop: 24, marginBottom: 8, fontSize: '1rem', color: '#94a3b8' }}>
        Detailed Comparison Table
      </h3>
      <table className="comparison-table">
        <thead>
          <tr>
            <th>Algorithm</th>
            <th>Avg Latency (ms)</th>
            <th>Exec Time (ms)</th>
            <th>CPU Utilization</th>
          </tr>
        </thead>
        <tbody>
          {comparison.map((c) => (
            <tr key={c.algorithm} className={c.algorithm === 'gnn' ? 'highlight-row' : ''}>
              <td>
                <span style={{ color: COLORS[c.algorithm], marginRight: 8 }}>●</span>
                {NICE_NAMES[c.algorithm] || c.algorithm}
                {c.algorithm === 'gnn' && ' 🏆'}
              </td>
              <td>{c.average_latency.toFixed(2)}</td>
              <td>{c.execution_time.toFixed(2)}</td>
              <td>{(c.cpu_utilization * 100).toFixed(1)}%</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
