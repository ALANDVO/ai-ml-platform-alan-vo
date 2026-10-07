import React from 'react';
import { ModelRecord } from '../api/client';

interface Props {
  model: ModelRecord;
  selected: boolean;
  onClick: () => void;
}

export default function ModelCard({ model, selected, onClick }: Props) {
  const latest = model.versions[model.versions.length - 1];
  const bestMetric = latest ? Math.max(...Object.values(latest.metrics).map((v) => v as number)) : 0;

  return (
    <div className={`model-card ${selected ? 'selected' : ''}`} onClick={onClick}>
      <div className="model-card-header">
        <h3>{model.name}</h3>
        <span className="badge">{model.task}</span>
      </div>
      <div className="model-card-meta">
        <span>Architecture: {model.architecture}</span>
        <span>{model.versions.length} version{model.versions.length !== 1 ? 's' : ''}</span>
      </div>
      {latest && (
        <div className="model-card-metrics">
          <div className="metric-highlight">
            <span>Best metric</span>
            <strong>{bestMetric.toFixed(4)}</strong>
          </div>
          <div className="model-card-tags">
            {latest.tags.map((t) => (
              <span key={t} className="badge">{t}</span>
            ))}
          </div>
        </div>
      )}
      <div className="model-card-footer">
        <span>Created {new Date(model.created_at * 1000).toLocaleDateString()}</span>
      </div>
    </div>
  );
}
