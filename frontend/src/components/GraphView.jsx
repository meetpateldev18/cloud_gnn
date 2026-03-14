import React, { useRef, useEffect } from 'react';

export default function GraphView({ data }) {
  const canvasRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !data.nodes.length) return;
    const ctx = canvas.getContext('2d');
    const W = canvas.width = canvas.parentElement.clientWidth;
    const H = canvas.height = 380;

    // Layout nodes in a circle
    const cx = W / 2, cy = H / 2, r = Math.min(W, H) * 0.35;
    const positions = {};
    data.nodes.forEach((n, i) => {
      const angle = (2 * Math.PI * i) / data.nodes.length - Math.PI / 2;
      positions[n.id] = { x: cx + r * Math.cos(angle), y: cy + r * Math.sin(angle) };
    });

    // Clear
    ctx.fillStyle = '#0f172a';
    ctx.fillRect(0, 0, W, H);

    // Draw edges
    ctx.strokeStyle = '#334155';
    ctx.lineWidth = 1;
    data.edges.forEach((e) => {
      const s = positions[e.source], t = positions[e.target];
      if (!s || !t) return;
      ctx.beginPath();
      ctx.moveTo(s.x, s.y);
      ctx.lineTo(t.x, t.y);
      ctx.stroke();
    });

    // Draw nodes
    data.nodes.forEach((n) => {
      const p = positions[n.id];
      const load = n.current_load || 0;
      const green = Math.round(255 * (1 - load));
      const red = Math.round(255 * load);
      ctx.fillStyle = `rgb(${red}, ${green}, 100)`;
      ctx.beginPath();
      ctx.arc(p.x, p.y, 14, 0, 2 * Math.PI);
      ctx.fill();
      ctx.strokeStyle = '#38bdf8';
      ctx.lineWidth = 2;
      ctx.stroke();

      // Label
      ctx.fillStyle = '#e2e8f0';
      ctx.font = '10px sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText(n.id.replace('machine-', 'M'), p.x, p.y + 26);
    });
  }, [data]);

  return (
    <div className="graph-container">
      <canvas ref={canvasRef} style={{ width: '100%', height: '380px' }} />
    </div>
  );
}
