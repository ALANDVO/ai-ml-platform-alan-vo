#!/usr/bin/env python3
"""AI ML Training Platform — main entry point."""
import sys, os, logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from config import settings
from utils.logging import setup_logging
from api.routes import router as api_router

setup_logging(settings.log_level)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="AI ML Training Platform",
    version="1.0.0",
    description="Enterprise ML training platform with experiment tracking, model registry, Bayesian hyperparameter optimization, LLM-powered architecture suggestions, and real-time training monitoring.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from api.middleware import request_logger, rate_limiter  # noqa: E402
app.middleware("http")(request_logger)
app.middleware("http")(rate_limiter)

app.include_router(api_router, prefix="/api")

frontend_dist = os.path.join(os.path.dirname(__file__), "frontend", "dist")
if os.path.isdir(frontend_dist):
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")

@app.on_event("startup")
async def _startup():
    from models.registry import model_registry
    from inference.serving import serving_pool
    model_registry.ensure_storage()
    serving_pool.start()
    logger.info("AI ML Training Platform started (pid=%d)", os.getpid())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=settings.host, port=settings.port, reload=False)
