# AI ML Training Platform

Enterprise ML training platform with experiment tracking, model registry, Bayesian hyperparameter optimization, LLM-powered architecture suggestions, and real-time training monitoring.

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                        React Frontend                         │
│  ┌─────────────┐  ┌───────────┐  ┌─────────┐  ┌──────────┐  │
│  │ Experiments │  │  Training │  │ Models  │  │  Compare │  │
│  │  Run List   │  │  Monitor  │  │ Registry│  │ A/B Diff │  │
│  └─────────────┘  └───────────┘  └─────────┘  └──────────┘  │
│  ┌─────────────┐  ┌─────────────────────────────────────────┐ │
│  │ Hyperparams │  │  TrainingChart / ModelCard / Sliders    │ │
│  │  Bayesian   │  │  (loss/accuracy curves, model cards)    │ │
│  └─────────────┘  └─────────────────────────────────────────┘ │
└───────────────────────────┬──────────────────────────────────┘
                            │ REST /api/*
┌───────────────────────────▼──────────────────────────────────┐
│                      FastAPI Backend                           │
│  ┌────────┐  ┌──────────────┐  ┌───────────────────────────┐  │
│  │ Auth   │  │  Middleware  │  │           Routes           │  │
│  │ SAML   │  │ Logging      │  │ /experiments /models /runs │  │
│  │ JWT    │  │ Rate Limit   │  │ /training /hyperparams /llm│  │
│  └────────┘  │ CORS         │  └───────────────────────────┘  │
│              └──────────────┘                                 │
│  ┌─────────────────────┐  ┌─────────────────────────────────┐ │
│  │   Training Engine    │  │        LLM Integration          │ │
│  │  Trainer + Callbacks │  │  Architecture Suggestions       │ │
│  │  Optimizers (Bayes)  │  │  Experiment Analysis            │ │
│  │  Registry + Versioning│ │                                  │ │
│  │  Serving + Batching  │  │                                  │ │
│  └─────────────────────┘  └─────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
```

## Quick Start

```bash
git clone https://github.com/ALANDVO/ai-ml-platform-alan-vo.git
cd ai-ml-platform-alan-vo
cp .env.example .env
docker compose up -d
# Open http://localhost:8000
```

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/auth/login` | SAML/SSO login or email login |
| `GET` | `/api/auth/me` | Get current user |
| `GET` | `/api/health` | Health check |
| `GET` | `/api/experiments` | List experiments |
| `POST` | `/api/experiments` | Create experiment |
| `GET` | `/api/experiments/{id}/runs` | Runs for an experiment |
| `GET` | `/api/runs/{id}` | Run details with metrics |
| `POST` | `/api/runs/{id}/stop` | Stop a running training run |
| `GET` | `/api/runs/{id}/metrics` | Metric curves for charting |
| `GET` | `/api/models` | Model registry |
| `POST` | `/api/models` | Register a model |
| `GET` | `/api/models/{id}/versions` | Version lineage |
| `POST` | `/api/models/{id}/rollback` | Roll back to a version |
| `POST` | `/api/models/compare` | A/B compare two model versions |
| `GET` | `/api/hyperparams/spaces` | Search spaces |
| `POST` | `/api/hyperparams/optimize` | Start Bayesian optimization |
| `GET` | `/api/hyperparams/optimize/{id}` | Optimization status |
| `POST` | `/api/llm/architecture` | LLM architecture suggestions |
| `POST` | `/api/llm/analyze` | LLM experiment analysis |
| `GET` | `/api/training/active` | Active training jobs |
| `GET` | `/api/inference/predict` | Served inference with batching |

## SSO / SAML Setup

1. Register your app in your IdP (Okta, ADFS, OneLogin) as a SAML Service Provider.
2. Set these in `.env`:
   - `SAML_IDP_ENTITY` — IdP entity ID
   - `SAML_IDP_CERT` — base64 IdP signing certificate
   - `SAML_SP_ENTITY` — this app's entity ID (`https://yourdomain.com/saml/sp`)
   - `SAML_ACS_URL` — Assertion Consumer Service URL
3. Map SAML attributes to roles: `admin` (full access), `ml_engineer` (training + registry), `viewer` (read-only).
4. Restart the container; users authenticate at `/api/auth/login` (SAML redirect) or with a JWT via the OAuth2 flow.

## Docker Deployment

```bash
docker compose up -d          # build + run
docker compose logs -f app    # follow logs
docker compose down           # stop
```

Production: scale workers with `uvicorn main:app --workers 4`, mount `/app/data` for artifacts and `/app/checkpoints` for checkpoints, and put the container behind a TLS-terminating reverse proxy.

---

**Built by [Alan Vo](https://github.com/ALANDVO)** | alanvo@gmail.com | AI, ML & Cybersecurity
