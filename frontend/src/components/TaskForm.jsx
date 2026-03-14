import React, { useState } from 'react';
import { scheduleTask } from '../api';

export default function TaskForm({ onResult }) {
  const [form, setForm] = useState({ cpu_required: 2.0, memory_required: 4.0, priority: 1 });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const res = await scheduleTask({
        cpu_required: parseFloat(form.cpu_required),
        memory_required: parseFloat(form.memory_required),
        priority: parseInt(form.priority, 10),
      });
      onResult(res.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Scheduling failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="card">
      <h2>📋 Submit Task for Scheduling</h2>
      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label>CPU Required (cores)</label>
          <input
            type="number"
            step="0.1"
            min="0.1"
            value={form.cpu_required}
            onChange={(e) => setForm({ ...form, cpu_required: e.target.value })}
          />
        </div>
        <div className="form-group">
          <label>Memory Required (GB)</label>
          <input
            type="number"
            step="0.5"
            min="0.5"
            value={form.memory_required}
            onChange={(e) => setForm({ ...form, memory_required: e.target.value })}
          />
        </div>
        <div className="form-group">
          <label>Priority (0-10)</label>
          <input
            type="number"
            min="0"
            max="10"
            value={form.priority}
            onChange={(e) => setForm({ ...form, priority: e.target.value })}
          />
        </div>
        <button className="btn btn-primary" type="submit" disabled={loading}>
          {loading ? 'Scheduling…' : '🚀 Schedule Task with GNN'}
        </button>
      </form>
      {error && <p style={{ color: '#f87171', marginTop: 12 }}>{error}</p>}
    </div>
  );
}
