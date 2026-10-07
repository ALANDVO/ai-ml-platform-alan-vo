import React, { useEffect, useState } from 'react';
import client, { ModelRecord, ModelVersion } from '../api/client';
import ModelCard from '../components/ModelCard';

export default function Models() {
  const [models, setModels] = useState<ModelRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<ModelRecord | null>(null);

  const load = async () => {
    setLoading(true);
    try {
      const res = await client.get('/models');
      setModels(res.data);
    } catch {
      setModels([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  return (
    <div className="page">
      <div className="page-header">
        <h2>Model Registry</h2>
      </div>
      {loading && <div className="empty">Loading…</div>}
      {!loading && models.length === 0 && (
        <div className="empty">No models registered. Train a run and register it here.</div>
      )}
      {!loading && models.length > 0 && (
        <div className="models-layout">
          <div className="models-list">
            {models.map((m) => (
              <ModelCard key={m.id} model={m} selected={selected?.id === m.id} onClick={() => setSelected(m)} />
            ))}
          </div>
          {selected && (
            <div className="models-detail">
              <h3>{selected.name}</h3>
              <p className="card-desc">{selected.description}</p>
              <div className="detail-meta">
                <span>Task: {selected.task}</span>
                <span>Architecture: {selected.architecture}</span>
              </div>
              <h4>Versions</h4>
              <table className="versions-table">
                <thead>
                  <tr><th>Version</th><th>Run</th><th>Tags</th><th>Metrics</th><th>Parent</th></tr>
                </thead>
                <tbody>
                  {selected.versions.map((v: ModelVersion) => (
                    <tr key={v.version}>
                      <td>v{v.version}</td>
                      <td>{v.run_id.slice(0, 8)}…</td>
                      <td>{v.tags.join(', ') || '—'}</td>
                      <td>{Object.entries(v.metrics).map(([k, val]) => `${k}: ${val.toFixed(4)}`).join(' | ')}</td>
                      <td>{v.parent_version ? `v${v.parent_version}` : '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
