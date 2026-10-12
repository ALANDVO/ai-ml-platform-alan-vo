import React, { useEffect, useState } from 'react';
import client, { ModelRecord, ModelVersion } from '../api/client';

interface CompareResult {
  model_id: string;
  version_a: number;
  version_b: number;
  a: { run_id: string; tags: string[]; metrics: Record<string, number> };
  b: { run_id: string; tags: string[]; metrics: Record<string, number> };
  diffs: Record<string, { a: number | null; b: number | null; delta: number | null; improvement_pct: number | null }>;
  winner: string;
}

export default function Compare() {
  const [models, setModels] = useState<ModelRecord[]>([]);
  const [modelId, setModelId] = useState('');
  const [versionA, setVersionA] = useState(1);
  const [versionB, setVersionB] = useState(2);
  const [result, setResult] = useState<CompareResult | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    client.get('/models').then((res) => {
      setModels(res.data);
      if (res.data.length > 0) {
        setModelId(res.data[0].id);
        const versions = res.data[0].versions.map((v: ModelVersion) => v.version);
        if (versions.length >= 2) {
          setVersionA(versions[0]);
          setVersionB(versions[versions.length - 1]);
        }
      }
    }).catch(() => {});
  }, []);

  const model = models.find((m) => m.id === modelId);
  const versions = model?.versions.map((v) => v.version) || [1];

  const compare = async () => {
    setError('');
    try {
      const res = await client.post('/models/compare', null, {
        params: { model_id: modelId, version_a: versionA, version_b: versionB },
      });
      setResult(res.data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Comparison failed');
      setResult(null);
    }
  };

  return (
    <div className="page">
      <div className="page-header">
        <h2>Model Comparison</h2>
      </div>
      <div className="card">
        <div className="form-inline">
          <select value={modelId} onChange={(e) => setModelId(e.target.value)}>
            {models.map((m) => <option key={m.id} value={m.id}>{m.name}</option>)}
          </select>
          <select value={versionA} onChange={(e) => setVersionA(Number(e.target.value))}>
            {versions.map((v) => <option key={v} value={v}>v{v}</option>)}
          </select>
          <span>vs</span>
          <select value={versionB} onChange={(e) => setVersionB(Number(e.target.value))}>
            {versions.map((v) => <option key={v} value={v}>v{v}</option>)}
          </select>
          <button className="btn-primary" onClick={compare}>Compare</button>
        </div>
        {error && <div className="login-error">{error}</div>}
      </div>

      {result && (
        <>
          <div className={`winner-banner winner-${result.winner}`}>
            🏆 Winner: {result.winner}
          </div>
          <div className="compare-grid">
            <div className="card">
              <h3>Version A (v{result.version_a})</h3>
              <div className="compare-tags">{result.a.tags.join(', ') || 'no tags'}</div>
              {Object.entries(result.a.metrics).map(([k, v]) => (
                <div key={k} className="compare-metric">{k}: {v.toFixed(4)}</div>
              ))}
            </div>
            <div className="card">
              <h3>Version B (v{result.version_b})</h3>
              <div className="compare-tags">{result.b.tags.join(', ') || 'no tags'}</div>
              {Object.entries(result.b.metrics).map(([k, v]) => (
                <div key={k} className="compare-metric">{k}: {v.toFixed(4)}</div>
              ))}
            </div>
          </div>
          <div className="card">
            <h3>Metric Deltas</h3>
            <table className="diffs-table">
              <thead>
                <tr><th>Metric</th><th>A</th><th>B</th><th>Delta</th><th>% Change</th></tr>
              </thead>
              <tbody>
                {Object.entries(result.diffs).map(([k, d]) => (
                  <tr key={k}>
                    <td>{k}</td>
                    <td>{d.a !== null ? d.a.toFixed(4) : '—'}</td>
                    <td>{d.b !== null ? d.b.toFixed(4) : '—'}</td>
                    <td className={d.delta !== null && d.delta < 0 ? 'diff-neg' : 'diff-pos'}>
                      {d.delta !== null ? d.delta.toFixed(4) : '—'}
                    </td>
                    <td>{d.improvement_pct !== null ? `${d.improvement_pct.toFixed(1)}%` : '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
