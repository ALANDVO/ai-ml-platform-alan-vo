import React from 'react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from 'recharts';
import { MetricPoint } from '../api/client';

interface Props {
  metrics: Record<string, MetricPoint[]>;
}

export default function TrainingChart({ metrics }: Props) {
  const metricNames = Object.keys(metrics);
  if (metricNames.length === 0) {
    return <div className="empty">No metrics yet — start a training run</div>;
  }

  const maxSteps = Math.max(...metricNames.map((n) => metrics[n].length), 1);
  const data: Record<string, number>[] = [];
  for (let i = 0; i < maxSteps; i++) {
    const row: Record<string, number> = { step: i };
    for (const name of metricNames) {
      const pts = metrics[name];
      if (i < pts.length) {
        row[name] = pts[i].value;
      }
    }
    data.push(row);
  }

  const colors = ['#6366f1', '#22c55e', '#f59e0b', '#ef4444', '#06b6d4'];

  return (
    <div className="training-chart">
      <h3>Training Metrics</h3>
      <ResponsiveContainer width="100%" height={320}>
        <LineChart data={data} margin={{ top: 10, right: 20, bottom: 10, left: 10 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
          <XAxis dataKey="step" stroke="#64748b" />
          <YAxis stroke="#64748b" domain={['auto', 'auto']} />
          <Tooltip contentStyle={{ background: '#0f172a', border: '1px solid #1e293b' }} />
          <Legend />
          {metricNames.map((name, idx) => (
            <Line
              key={name}
              type="monotone"
              dataKey={name}
              stroke={colors[idx % colors.length]}
              dot={false}
              strokeWidth={2}
              connectNulls
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
