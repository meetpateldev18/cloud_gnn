import React from 'react';

const STATUS_COLOR = {
  running:   '#fbbf24',
  completed: '#4ade80',
  queued:    '#94a3b8',
};

export default function TaskList({ tasks }) {
  if (!tasks || tasks.length === 0) return null;

  const running   = tasks.filter((t) => t.status === 'running');
  const completed = tasks.filter((t) => t.status === 'completed');

  return (
    <div className="card">
      <h2>
        📋 Live Task Monitor &nbsp;
        <span style={{ fontSize: '0.85rem', color: '#fbbf24' }}>
          {running.length} running
        </span>
        &nbsp;/&nbsp;
        <span style={{ fontSize: '0.85rem', color: '#4ade80' }}>
          {completed.length} completed
        </span>
      </h2>
      <div style={{ overflowX: 'auto' }}>
        <table className="comparison-table">
          <thead>
            <tr>
              <th>Task ID</th>
              <th>Status</th>
              <th>Machine</th>
              <th>CPU Req</th>
              <th>RAM Req (GB)</th>
              <th>Priority</th>
              <th>Duration (s)</th>
              <th>Wait (ms)</th>
            </tr>
          </thead>
          <tbody>
            {tasks.slice(0, 20).map((t) => (
              <tr key={t.id}>
                <td>#{t.id}</td>
                <td>
                  <span style={{
                    color: STATUS_COLOR[t.status] || '#94a3b8',
                    fontWeight: 600,
                    textTransform: 'capitalize',
                  }}>
                    ● {t.status}
                  </span>
                </td>
                <td>{t.assigned_machine_id || '—'}</td>
                <td>{t.cpu_request}</td>
                <td>{t.memory_request}</td>
                <td>{t.priority}</td>
                <td>{t.execution_duration?.toFixed(1) ?? '—'}</td>
                <td>{t.waiting_time != null ? (t.waiting_time * 1000).toFixed(1) : '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
