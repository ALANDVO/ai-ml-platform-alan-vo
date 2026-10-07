import React from 'react';
import { Routes, Route, Navigate, NavLink } from 'react-router-dom';
import { useAuth } from './auth/AuthContext';
import Login from './pages/Login';
import Experiments from './pages/Experiments';
import Training from './pages/Training';
import Models from './pages/Models';
import Compare from './pages/Compare';
import Hyperparams from './pages/Hyperparams';

export default function App() {
  const { user, loading } = useAuth();

  if (loading) {
    return <div className="app-loading">Loading…</div>;
  }

  if (!user) {
    return <Login />;
  }

  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="app-brand">
          <span className="app-logo">🧠</span>
          <div>
            <div className="app-title">AI ML Training Platform</div>
            <div className="app-subtitle">Experiments · Models · Optimization</div>
          </div>
        </div>
        <nav className="app-nav">
          <NavLink to="/experiments" className={({ isActive }) => (isActive ? 'active' : '')}>Experiments</NavLink>
          <NavLink to="/training" className={({ isActive }) => (isActive ? 'active' : '')}>Training</NavLink>
          <NavLink to="/models" className={({ isActive }) => (isActive ? 'active' : '')}>Models</NavLink>
          <NavLink to="/compare" className={({ isActive }) => (isActive ? 'active' : '')}>Compare</NavLink>
          <NavLink to="/hyperparams" className={({ isActive }) => (isActive ? 'active' : '')}>Hyperparams</NavLink>
        </nav>
        <div className="app-user">
          <span>{user.name}</span>
          <span className="badge">{user.role}</span>
        </div>
      </header>
      <main className="app-main">
        <Routes>
          <Route path="/" element={<Navigate to="/experiments" replace />} />
          <Route path="/experiments" element={<Experiments />} />
          <Route path="/training" element={<Training />} />
          <Route path="/models" element={<Models />} />
          <Route path="/compare" element={<Compare />} />
          <Route path="/hyperparams" element={<Hyperparams />} />
          <Route path="*" element={<Navigate to="/experiments" replace />} />
        </Routes>
      </main>
    </div>
  );
}
