# Product development plan

Each round completes one feature or repair. Future items are planned, not implemented claims.

## Current round

full-stack-baseline-and-packaging

## Roadmap

### full-stack-baseline-and-packaging — Full-stack modular layout, CI workflow, and container packaging baseline

Status: done

Acceptance:
- Backend relocated to standard backend/app and backend/tests with runnable FastAPI entrypoint and passing pytest suite
- Frontend verified with TypeScript build and vitest component test suite
- Packaging essentials in place: backend/Dockerfile, frontend/Dockerfile, compose.yaml with Keycloak service, and .github/workflows/ci.yml
- Preflight and structural checks pass cleanly

Implementation: `backend/app/main.py`, `backend/app/api/routes.py`, `backend/app/api/middleware.py`, `frontend/src/App.tsx`, `compose.yaml`, `backend/Dockerfile`, `frontend/Dockerfile`, `.github/workflows/ci.yml`

Tests: `backend/tests/test_core.py`, `backend/tests/test_api_integration.py`, `frontend/src/components/ModelCard.test.tsx`

### dynamic-batching-benchmarks — Inference server dynamic batching throughput benchmarks

Status: in_progress

Acceptance:
- Benchmarking harness measuring latency vs queue depth under simulated inference loads
- Adaptive timeout adjustment under variable concurrency

Implementation: `backend/app/inference/benchmarks.py`, `backend/tests/test_benchmarks.py`

Tests: `backend/tests/test_benchmarks.py`

