from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from enum import Enum
import time

class Role(str, Enum):
    admin = "admin"
    ml_engineer = "ml_engineer"
    viewer = "viewer"

class User(BaseModel):
    id: str
    email: str
    name: str
    role: Role = Role.viewer

class ExperimentStatus(str, Enum):
    active = "active"
    completed = "completed"
    archived = "archived"

class RunStatus(str, Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"
    stopped = "stopped"

class ExperimentCreate(BaseModel):
    name: str
    description: str = ""
    dataset: str = ""
    framework: str = "pytorch"

class Experiment(BaseModel):
    id: str
    name: str
    description: str
    dataset: str
    framework: str
    status: ExperimentStatus = ExperimentStatus.active
    created_at: float = Field(default_factory=time.time)
    run_count: int = 0

class MetricPoint(BaseModel):
    step: int
    value: float
    ts: float = Field(default_factory=time.time)

class Run(BaseModel):
    id: str
    experiment_id: str
    name: str
    config: Dict[str, Any] = {}
    hyperparams: Dict[str, Any] = {}
    status: RunStatus = RunStatus.pending
    metrics: Dict[str, List[MetricPoint]] = {}
    best_metric: Optional[float] = None
    best_metric_name: str = "loss"
    started_at: Optional[float] = None
    finished_at: Optional[float] = None
    created_at: float = Field(default_factory=time.time)

class RunCreate(BaseModel):
    name: str
    hyperparams: Dict[str, Any] = {}
    config: Dict[str, Any] = {}

class ModelVersion(BaseModel):
    version: int
    run_id: str
    registered_at: float = Field(default_factory=time.time)
    tags: List[str] = []
    metrics: Dict[str, float] = {}
    parent_version: Optional[int] = None
    rollback_target: Optional[int] = None

class ModelRecord(BaseModel):
    id: str
    name: str
    description: str = ""
    task: str = "classification"
    architecture: str = "mlp"
    versions: List[ModelVersion] = []
    created_at: float = Field(default_factory=time.time)

class ModelRegister(BaseModel):
    name: str
    description: str = ""
    task: str = "classification"
    architecture: str = "mlp"
    run_id: str
    tags: List[str] = []
    metrics: Dict[str, float] = {}

class HyperparamSpec(BaseModel):
    name: str
    type: str  # float | int | categorical | logfloat
    low: Optional[float] = None
    high: Optional[float] = None
    base: Optional[float] = None
    choices: Optional[List[str]] = []

class SearchSpace(BaseModel):
    id: str
    name: str
    objective: str = "minimize"
    params: List[HyperparamSpec] = []
    created_at: float = Field(default_factory=time.time)

class SpaceCreate(BaseModel):
    name: str
    objective: str = "minimize"
    params: List[HyperparamSpec]

class OptimizeRequest(BaseModel):
    space_id: str
    n_trials: int = 20
    experiment_id: Optional[str] = None

class OptimizationTrial(BaseModel):
    trial_id: int
    params: Dict[str, Any]
    score: Optional[float] = None
    status: str = "pending"
    duration_s: float = 0.0

class OptimizationStatus(BaseModel):
    id: str
    space_id: str
    status: str = "running"  # running | completed | failed
    trials: List[OptimizationTrial] = []
    best_params: Optional[Dict[str, Any]] = None
    best_score: Optional[float] = None
    started_at: float = Field(default_factory=time.time)
    finished_at: Optional[float] = None

class ArchitectureRequest(BaseModel):
    task: str
    dataset_size: int = 10000
    features: int = 128
    constraints: str = ""

class AnalyzeRequest(BaseModel):
    experiment_ids: List[str]
    focus: str = "overall"

class PredictRequest(BaseModel):
    model_id: str
    version: int = 1
    inputs: List[List[float]]

class PredictResponse(BaseModel):
    model_id: str
    version: int
    predictions: List[List[float]]
    batch_id: str
    latency_ms: float

class TrainingJob(BaseModel):
    run_id: str
    name: str
    experiment_id: str
    status: str
    step: int = 0
    total_steps: int = 0
    progress: float = 0.0
    loss: Optional[float] = None
    accuracy: Optional[float] = None
    eta_s: Optional[float] = None

class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = "1.0.0"
    active_runs: int = 0
    registered_models: int = 0
    uptime_s: float = 0.0
