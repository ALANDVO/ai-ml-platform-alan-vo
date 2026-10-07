import React, { useEffect, useState } from 'react';
import client, { Experiment } from '../api/client';
import { useNavigate } from 'react-router-dom';

export default function Experiments() {
  const [experiments, setExperiments] = useState<Experiment[]>([]);
  const [loading, setLoading] = useState(true);
  const [showNew, setShowNew] = useState(false);
  const [newName, setNewName] = useState('');
  const [newDataset, setNewDataset] = useState('mnist');
  const navigate = useNavigate();

  const load = async () => {
    setLoading(true);
    try {
      const res = await client.get('/experiments');
      setExperiments(res.data);
    } catch {
      setExperiments([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const create = async (e: React.FormEvent) => {
    e.preventDefault();
    await client.post('/experiments', { name: newName, dataset: newDataset, framework: 'pytorch' });
    setNewName('');
    setShowNew(false);
    load();
  };

  return (
    <div className="page">
      <div className="page-header">
        <h2>Experiments</h2>
        <button className="btn-primary" onClick={() => setShowNew(true)}>+ New Experiment</button>
      </div>

      {showNew && (
        <form className="card form-inline" onSubmit={create}>
          <input placeholder="Experiment name" value={newName} onChange={(e) => setNewName(e.target.value)} required />
          <select value={newDataset} onChange={(e) => setNewDataset(e.target.value)}>
            <option value="mnist">MNIST</option>
            <option value="cifar10">CIFAR-10</option>
            <option value="imdb">IMDB</option>
            <option value="tabular">Tabular</option>
          </select>
          <button type="submit">Create</button>
          <button type="button" onClick={() => setShowNew(false)}>Cancel</button>
        </form>
      )}

      {loading ? (
        <div className="empty">Loading…</div>
      ) : experiments.length === 0 ? (
        <div className="empty">No experiments yet. Create one to start tracking runs.</div>
      ) : (
        <div className="card-grid">
          {experiments.map((exp) => (
            <div key={exp.id} className="card" onClick={() => navigate(`/training?exp=${exp.id}`)}>
              <div className="card-header">
                <h3>{exp.name}</h3>
                <span className={`badge badge-${exp.status}`}>{exp.status}</span>
              </div>
              <p className="card-desc">{exp.description || 'No description'}</p>
              <div className="card-meta">
                <span>📊 {exp.dataset}</span>
                <span>⚙️ {exp.framework}</span>
                <span>🔬 {exp.run_count} runs</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
