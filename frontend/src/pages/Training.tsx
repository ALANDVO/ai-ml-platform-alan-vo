import React, { useEffect, useState, useRef } from 'react';
import client, { Run, TrainingJob, MetricPoint } from '../api/client';
import { useSearchParams } from 'react-router-dom';
import TrainingChart from '../components/TrainingChart';

export default function Training() {
  const [searchParams] = useSearchParams();
  const expId = searchParams.get('exp');
  const [runs, setRuns] = useState<Run[]>([]);
  const [jobs, setJobs] = useState<TrainingJob[]>([]);
  const [selectedRun, setSelectedRun] = useState<Run | null>(null);
  const [metrics, setMetrics] = useState<Record<string, MetricPoint[]>>({});
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        const active = await client.get('/training/active');
        setJobs(active.data);
        if (expId) {
          const expRuns = await client.get(`/experiments/${expId}/runs`);
          setRuns(expRuns.data);
          if (expRuns.data.length > 0 && !selectedRun) {
            setSelectedRun(expRuns.data[0]);
          }
        } else if (runs.length === 0) {
          const all = await client.get('/experiments');
          if (all.data.length > 0) {
            const expRuns = await client.get(`/experiments/${all.data[0].id}/runs`);
            setRuns(expRuns.data);
            if (expRuns.data.length > 0 && !selectedRun) {
              setSelectedRun(expRuns.data[0]);
            }
          }
        }
      } catch { /* ignore */ }
    };
    load();
    pollRef.current = setInterval(load, 2000);
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, [expId]);

  useEffect(() => {
    if (!selectedRun) return;
    const loadMetrics = async () => {
      try {
        const res = await client.get(`/runs/${selectedRun.id}/metrics`);
        setMetrics(res.data);
      } catch { /* ignore */ }
    };
    loadMetrics();
    const iv = setInterval(loadMetrics, 2000);
    return () => clearInterval(iv);
  }, [selectedRun]);

  const startRun = async () => {
    const targetExp = expId || runs[0]?.experiment_id;
    if (!targetExp) return;
    await client.post(`/training/start?exp_id=${targetExp}`, {
      name: `run-${Date.now()}`,
      hyperparams: { epochs: 20, learning_rate: 0.01, batch_size: 32, hidden_units: 64 },
      config: {},
    });
  };

  return (
    <div className="page">
      <div className="page-header">
        <h2>Training</h2>
        <button className="btn-primary" onClick={startRun}>Start Run</button>
      </div>

      <div className="training-layout">
        <div className="training-sidebar">
          <h3>Active Jobs</h3>
          {jobs.length === 0 && <p className="empty">No active training jobs</p>}
          {jobs.map((job) => (
            <div key={job.run_id} className="job-card">
              <div className="job-header">
                <span>{job.name}</span>
                <span className={`badge badge-${job.status}`}>{job.status}</span>
              </div>
              <div className="progress-bar">
                <div className="progress-fill" style={{ width: `${job.progress * 100}%` }} />
              </div>
              <div className="job-stats">
                {job.loss !== null && <span>loss: {job.loss.toFixed(4)}</span>}
                {job.accuracy !== null && <span>acc: {job.accuracy.toFixed(4)}</span>}
              </div>
            </div>
          ))}

          <h3>Run History</h3>
          {runs.length === 0 && <p className="empty">No runs yet</p>}
          {runs.map((run) => (
            <div
              key={run.id}
              className={`run-item ${selectedRun?.id === run.id ? 'active' : ''}`}
              onClick={() => setSelectedRun(run)}
            >
              <span>{run.name}</span>
              <span className={`badge badge-${run.status}`}>{run.status}</span>
              {run.best_metric !== null && <span className="run-score">{run.best_metric.toFixed(4)}</span>}
            </div>
          ))}
        </div>

        <div className="training-main">
          {selectedRun ? (
            <>
              <div className="run-info">
                <h3>{selectedRun.name}</h3>
                <div className="run-hyperparams">
                  {Object.entries(selectedRun.hyperparams).map(([k, v]) => (
                    <span key={k} className="badge">{k}: {String(v)}</span>
                  ))}
                </div>
              </div>
              <TrainingChart metrics={metrics} />
            </>
          ) : (
            <div className="empty">Select a run to view metrics</div>
          )}
        </div>
      </div>
    </div>
  );
}
