"""Experiment and run tracking with metric storage."""
import os, json, time, uuid, logging
from typing import List, Optional, Dict, Any

from api.schemas import Experiment, Run, RunStatus, RunCreate, MetricPoint

logger = logging.getLogger(__name__)
_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")


class ExperimentStore:
    def __init__(self, path: str = "".join([_DATA_DIR, "experiments.json"])):
        self.path = path
        self._experiments: Dict[str, Experiment] = {}
        self._load()

    def _load(self):
        if os.path.exists(self.path):
            with open(self.path) as f:
                for item in json.load(f):
                    e = Experiment(**item)
                    self._experiments[e.id] = e

    def _save(self):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, "w") as f:
            json.dump([e.model_dump() for e in self._experiments.values()], f, indent=2)

    def list_experiments(self) -> List[Experiment]:
        return sorted(self._experiments.values(), key=lambda e: e.created_at, reverse=True)

    def get(self, exp_id: str) -> Optional[Experiment]:
        return self._experiments.get(exp_id)

    def create(self, **kwargs) -> Experiment:
        exp = Experiment(**kwargs)
        self._experiments[exp.id] = exp
        self._save()
        return exp


class RunRegistry:
    def __init__(self, path: str = os.path.join(_DATA_DIR, "runs.json")):
        self.path = path
        self._runs: Dict[str, Run] = {}
        self._load()

    def _load(self):
        if os.path.exists(self.path):
            with open(self.path) as f:
                for item in json.load(f):
                    r = Run(**item)
                    self._runs[r.id] = r

    def _save(self):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, "w") as f:
            json.dump([r.model_dump() for r in self._runs.values()], f, indent=2)

    def all(self) -> List[Run]:
        return sorted(self._runs.values(), key=lambda r: r.created_at, reverse=True)

    def get(self, run_id: str) -> Optional[Run]:
        return self._runs.get(run_id)

    def list_for_experiment(self, exp_id: str) -> List[Run]:
        return [r for r in self.all() if r.experiment_id == exp_id]

    def experiment_exists(self, exp_id: str) -> bool:
        return exp_id in [e.id for e in experiment_store.list_experiments()]

    def create(self, experiment_id: str, body: RunCreate) -> Run:
        run = Run(
            id=str(uuid.uuid4()),
            experiment_id=experiment_id,
            name=body.name,
            hyperparams=body.hyperparams,
            config=body.config,
            status=RunStatus.pending,
        )
        self._runs[run.id] = run
        experiment_store._experiments[experiment_id].run_count += 1
        self._save()
        experiment_store._save()
        return run

    def stop(self, run_id: str):
        run = self._runs.get(run_id)
        if run:
            run.status = RunStatus.stopped
            run.finished_at = time.time()
            self._save()


experiment_store = ExperimentStore()
run_registry = RunRegistry()
