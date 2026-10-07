import uuid, time
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse

from api.auth import get_current_user, saml_login, oauth_login
from api.schemas import (
    User, Experiment, ExperimentCreate, Run, RunCreate, RunStatus,
    ModelRecord, ModelRegister, ModelVersion,
    SearchSpace, SpaceCreate, OptimizeRequest, OptimizationStatus,
    ArchitectureRequest, AnalyzeRequest, PredictRequest, PredictResponse,
    HealthResponse, TrainingJob,
)
from config import settings

router = APIRouter(tags=["ml-platform"])

@router.get("/health")
async def health():
    from models.registry import model_registry
    from experiments.tracking import run_registry
    return HealthResponse(
        active_runs=sum(1 for r in run_registry.all() if r.status == RunStatus.running),
        registered_models=len(model_registry.all()),
        uptime_s=time.time() - _START,
    )

_START = time.time()

# ── Auth ──
@router.post("/auth/login")
async def login(email: str, password: str = ""):
    role = Role.admin.value if email.endswith("@alanvo.com") else Role.ml_engineer.value
    token = saml_login(email, email.split("@")[0], role)
    return {"token": token, "token_type": "bearer"}

@router.get("/auth/me")
async def me(user: User = Depends(get_current_user)):
    return user

@router.get("/auth/saml/redirect")
async def saml_redirect():
    return RedirectResponse(url=f"{settings.saml_idp_entity}/saml2/redirect?sp={settings.saml_sp_entity}")

@router.get("/auth/saml/acs")
async def saml_acs(SAMLResponse: str = ""):
    from utils.saml import verify_saml_response
    user = verify_saml_response(SAMLResponse)
    token = saml_login(user["email"], user["name"], user["role"])
    return {"token": token, "token_type": "bearer"}

# ── Experiments ──
@router.get("/experiments")
async def list_experiments(status: Optional[str] = None):
    from experiments.tracking import experiment_store
    out = experiment_store.list_experiments()
    if status:
        out = [e for e in out if e.status.value == status]
    return out

@router.post("/experiments", status_code=201)
async def create_experiment(body: ExperimentCreate, user: User = Depends(get_current_user)):
    if user.role.value == "viewer":
        raise HTTPException(403, "Viewer role cannot create experiments")
    from experiments.tracking import experiment_store
    exp = experiment_store.create(
        id=str(uuid.uuid4()), name=body.name, description=body.description,
        dataset=body.dataset, framework=body.framework,
    )
    return exp

@router.get("/experiments/{exp_id}/runs")
async def experiment_runs(exp_id: str):
    from experiments.tracking import run_registry
    if not run_registry.experiment_exists(exp_id):
        raise HTTPException(404, "Experiment not found")
    return run_registry.list_for_experiment(exp_id)

@router.get("/runs/{run_id}")
async def get_run(run_id: str):
    from experiments.tracking import run_registry
    run = run_registry.get(run_id)
    if not run:
        raise HTTPException(404, "Run not found")
    return run

@router.get("/runs/{run_id}/metrics")
async def run_metrics(run_id: str, metric: Optional[str] = None):
    from experiments.tracking import run_registry
    run = run_registry.get(run_id)
    if not run:
        raise HTTPException(404, "Run not found")
    if metric:
        return {"metric": metric, "points": run.metrics.get(metric, [])}
    return {k: v for k, v in run.metrics.items()}

@router.post("/runs/{run_id}/stop")
async def stop_run(run_id: str):
    from experiments.tracking import run_registry
    run = run_registry.get(run_id)
    if not run:
        raise HTTPException(404, "Run not found")
    run_registry.stop(run_id)
    return {"status": "stopped"}

# ── Training ──
@router.post("/training/start")
async def start_training(exp_id: str, body: RunCreate, user: User = Depends(get_current_user)):
    from training.trainer import training_pool
    run = await training_pool.start_run(exp_id, body)
    return run

@router.get("/training/active")
async def active_trainings():
    from training.trainer import training_pool
    return training_pool.active_jobs()

# ── Models ──
@router.get("/models")
async def list_models():
    from models.registry import model_registry
    return model_registry.all()

@router.post("/models", status_code=201)
async def register_model(body: ModelRegister, user: User = Depends(get_current_user)):
    from models.registry import model_registry
    record = model_registry.register(body)
    return record

@router.get("/models/{model_id}/versions")
async def model_versions(model_id: str):
    from models.registry import model_registry
    record = model_registry.get(model_id)
    if not record:
        raise HTTPException(404, "Model not found")
    return record.versions

@router.post("/models/{model_id}/rollback")
async def model_rollback(model_id: str, version: int, user: User = Depends(get_current_user)):
    from models.versioning import versioning
    record = versioning.rollback(model_id, version)
    return record

@router.post("/models/compare")
async def compare_models(model_id: str, version_a: int, version_b: int):
    from models.versioning import versioning
    return versioning.compare(model_id, version_a, version_b)

# ── Hyperparameters ──
@router.get("/hyperparams/spaces")
async def list_spaces():
    from experiments.hyperparams import space_store
    return space_store.list_spaces()

@router.post("/hyperparams/spaces", status_code=201)
async def create_space(body: SpaceCreate, user: User = Depends(get_current_user)):
    from experiments.hyperparams import space_store
    space = space_store.create(body)
    return space

@router.post("/hyperparams/optimize")
async def start_optimization(body: OptimizeRequest):
    from experiments.hyperparams import optimizer_store
    opt = await optimizer_store.start(body)
    return opt

@router.get("/hyperparams/optimize/{opt_id}")
async def optimization_status(opt_id: str):
    from experiments.hyperparams import optimizer_store
    opt = optimizer_store.get(opt_id)
    if not opt:
        raise HTTPException(404, "Optimization not found")
    return opt

# ── LLM ──
@router.post("/llm/architecture")
async def architecture_suggestions(body: ArchitectureRequest):
    from experiments.analysis import llm_architect
    return await llm_architect.suggest(body)

@router.post("/llm/analyze")
async def analyze_experiments(body: AnalyzeRequest):
    from experiments.analysis import llm_analyst
    return await llm_analyst.analyze(body)

# ── Inference ──
@router.post("/inference/predict")
async def predict(body: PredictRequest):
    from inference.serving import serving_pool
    return await serving_pool.predict(body)
