import axios from 'axios';

const client = axios.create({
  baseURL: '/api',
  timeout: 60000,
});

client.interceptors.request.use((config) => {
  const token = localStorage.getItem('ml_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

client.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('ml_token');
      window.location.href = '/';
    }
    return Promise.reject(err);
  },
);

export interface Experiment {
  id: string;
  name: string;
  description: string;
  dataset: string;
  framework: string;
  status: string;
  created_at: number;
  run_count: number;
}

export interface Run {
  id: string;
  experiment_id: string;
  name: string;
  hyperparams: Record<string, unknown>;
  config: Record<string, unknown>;
  status: string;
  best_metric: number | null;
  best_metric_name: string;
  started_at: number | null;
  finished_at: number | null;
  created_at: number;
}

export interface MetricPoint {
  step: number;
  value: number;
  ts: number;
}

export interface ModelRecord {
  id: string;
  name: string;
  description: string;
  task: string;
  architecture: string;
  versions: ModelVersion[];
  created_at: number;
}

export interface ModelVersion {
  version: number;
  run_id: string;
  registered_at: number;
  tags: string[];
  metrics: Record<string, number>;
  parent_version: number | null;
}

export interface TrainingJob {
  run_id: string;
  name: string;
  experiment_id: string;
  status: string;
  step: number;
  loss: number | null;
  accuracy: number | null;
  progress: number;
}

export interface SearchSpace {
  id: string;
  name: string;
  objective: string;
  params: HyperparamSpec[];
}

export interface HyperparamSpec {
  name: string;
  type: string;
  low?: number;
  high?: number;
  choices?: string[];
}

export interface OptimizationStatus {
  id: string;
  space_id: string;
  status: string;
  trials: OptimizationTrial[];
  best_params: Record<string, unknown> | null;
  best_score: number | null;
}

export interface OptimizationTrial {
  trial_id: number;
  params: Record<string, unknown>;
  score: number | null;
  status: string;
}

export default client;
