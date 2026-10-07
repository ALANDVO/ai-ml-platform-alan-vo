import React, { useEffect, useState } from 'react';
import client, { SearchSpace, HyperparamSpec, OptimizationStatus } from '../api/client';
import HyperparamSlider from '../components/HyperparamSlider';

export default function Hyperparams() {
  const [spaces, setSpaces] = useState<SearchSpace[]>([]);
  const [space, setSpace] = useState<SearchSpace | null>(null);
  const [params, setParams] = useState<Record<string, number | string>>({});
  const [nTrials, setNTrials] = useState(10);
  const [optimization, setOptimization] = useState<OptimizationStatus | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    client.get('/hyperparams/spaces').then((res) => {
      setSpaces(res.data);
      if (res.data.length > 0) {
        setSpace(res.data[0]);
        const initial: Record<string, number | string> = {};
        res.data[0].params.forEach((p) => {
          if (p.type === 'categorical') initial[p.name] = p.choices?.[0] || '';
          else initial[p.name] = (p.low ?? 0) + ((p.high ?? 1) - (p.low ?? 0)) / 2;
        });
        setParams(initial);
      }
    }).catch(() => {});
  }, []);

  const updateParam = (name: string, value: number | string) => {
    setParams((prev) => ({ ...prev, [name]: value }));
  };

  const startOptimization = async () => {
    if (!space) return;
    setBusy(true);
    try {
      const res = await client.post('/hyperparams/optimize', {
        space_id: space.id,
        n_trials: nTrials,
      });
      const optId = res.data.id;
      const poll = async () => {
        const status = await client.get(`/hyperparams/optimize/${optId}`);
        setOptimization(status.data);
        if (status.data.status === 'running') {
          setTimeout(poll, 2000);
        } else {
          setBusy(false);
        }
      };
      await poll();
    } catch (err) {
      console.error(err);
      setBusy(false);
    }
  };

  return (
    <div className="page">
      <div className="page-header">
        <h2>Hyperparameter Tuning</h2>
      </div>

      <div className="card">
        <div className="form-inline">
          <select
            value={space?.id || ''}
            onChange={(e) => {
              const s = spaces.find((sp) => sp.id === e.target.value) || null;
              setSpace(s);
              if (s) {
                const initial: Record<string, number | string> = {};
                s.params.forEach((p) => {
                  if (p.type === 'categorical') initial[p.name] = p.choices?.[0] || '';
                  else initial[p.name] = (p.low ?? 0) + ((p.high ?? 1) - (p.low ?? 0)) / 2;
                });
                setParams(initial);
              }
            }}
          >
            {spaces.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
          </select>
          <label>
            Trials
            <input type="number" min={1} max={100} value={nTrials} onChange={(e) => setNTrials(Number(e.target.value))} />
          </label>
          <button className="btn-primary" onClick={startOptimization} disabled={busy || !space}>
            {busy ? 'Running…' : 'Start Bayesian Optimization'}
          </button>
        </div>
      </div>

      {space && (
        <div className="card">
          <h3>Search Space</h3>
          <div className="sliders-grid">
            {space.params.map((p: HyperparamSpec) => (
              <HyperparamSlider
                key={p.name}
                spec={p}
                value={params[p.name] ?? 0}
                onChange={(v) => updateParam(p.name, v)}
              />
            ))}
          </div>
        </div>
      )}

      {optimization && (
        <div className="card">
          <div className="page-header">
            <h3>Optimization Status</h3>
            <span className={`badge badge-${optimization.status}`}>{optimization.status}</span>
          </div>
          {optimization.best_score !== null && (
            <div className="best-result">
              Best score: <strong>{optimization.best_score.toFixed(6)}</strong>
              {optimization.best_params && (
                <div className="best-params">
                  {Object.entries(optimization.best_params).map(([k, v]) => (
                    <span key={k} className="badge">{k}={String(v)}</span>
                  ))}
                </div>
              )}
            </div>
          )}
          <table className="trials-table">
            <thead>
              <tr><th>Trial</th><th>Params</th><th>Score</th><th>Status</th></tr>
            </thead>
            <tbody>
              {optimization.trials.map((t) => (
                <tr key={t.trial_id}>
                  <td>#{t.trial_id}</td>
                  <td className="trial-params">{Object.entries(t.params).map(([k, v]) => `${k}=${String(v)}`).join(', ')}</td>
                  <td>{t.score !== null ? t.score.toFixed(6) : '—'}</td>
                  <td>{t.status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
