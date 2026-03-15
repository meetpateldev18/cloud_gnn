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
              <th>CPU Total</th>
              <th>CPU Avail</th>
              <th>RAM Total (GB)</th>
              <th>RAM Avail (GB)</th>
              <th>Bandwidth (Gbps)</th>
              <th>Load</th>
            </tr>
          </thead>
          <tbody>
            {machines.map((m) => {
              const loadPct = (m.load * 100).toFixed(1);
              const loadColor = m.load > 0.7 ? '#f87171' : m.load > 0.4 ? '#fbbf24' : '#4ade80';
              const cpuPct = m.total_cpu > 0 ? ((m.available_cpu / m.total_cpu) * 100).toFixed(0) : 0;
              const ramPct = m.total_ram > 0 ? ((m.available_ram / m.total_ram) * 100).toFixed(0) : 0;
              return (
                <tr key={m.machine_id}>
                  <td>{m.machine_id}</td>
                  <td>{m.total_cpu}</td>
                  <td>
                    <span style={{ color: cpuPct < 20 ? '#f87171' : '#4ade80' }}>
                      {m.available_cpu} ({cpuPct}% free)
                    </span>
                  </td>
                  <td>{m.total_ram}</td>
                  <td>
                    <span style={{ color: ramPct < 20 ? '#f87171' : '#4ade80' }}>
                      {m.available_ram?.toFixed(1)} ({ramPct}% free)
                    </span>
                  </td>
                  <td>{m.bandwidth}</td>
                  <td>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <div style={{
                        width: 60, height: 8, background: '#1e293b', borderRadius: 4, overflow: 'hidden',
                      }}>
                        <div style={{
                          width: `${loadPct}%`, height: '100%', background: loadColor, borderRadius: 4,
                        }} />
                      </div>
                      <span style={{ color: loadColor }}>{loadPct}%</span>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
