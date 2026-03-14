import React from 'react';

export default function MachineTable({ machines }) {
  if (!machines || machines.length === 0) return null;

  return (
    <div className="card">
      <h2>🖥️ Registered Machines</h2>
      <div style={{ overflowX: 'auto' }}>
        <table className="comparison-table">
          <thead>
            <tr>
              <th>Machine ID</th>
              <th>CPU</th>
              <th>RAM (GB)</th>
              <th>Bandwidth</th>
              <th>Load</th>
            </tr>
          </thead>
          <tbody>
            {machines.map((m) => (
              <tr key={m.machine_id}>
                <td>{m.machine_id}</td>
                <td>{m.cpu_capacity}</td>
                <td>{m.ram_capacity}</td>
                <td>{m.network_bandwidth}</td>
                <td>
                  <span style={{
                    color: m.current_load > 0.7 ? '#f87171' : m.current_load > 0.4 ? '#fbbf24' : '#4ade80'
                  }}>
                    {(m.current_load * 100).toFixed(1)}%
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
