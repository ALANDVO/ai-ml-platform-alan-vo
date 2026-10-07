"""Hyperparameter search spaces and Bayesian optimization orchestration."""
import os, json, time, uuid, asyncio, logging
from typing import List, Dict, Any, Optional

from api.schemas import SearchSpace, SpaceCreate, OptimizeRequest, OptimizationStatus, OptimizationTrial

logger = logging.getLogger(__name__)
_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")


class SpaceStore:
    def __init__(self, path: str = os.path.join(_DATA_DIR, "spaces.json")):
        self.path = path
        self._spaces: Dict[str, SearchSpace] = {}
        if os.path.exists(self.path):
            with open(self.path) as f:
                for item in json.load(f):
                    s = SearchSpace(**item)
                    self._spaces[s.id] = s

    def _save(self):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, "w") as f:
            json.dump([s.model_dump() for s in self._spaces.values()], f, indent=2)

    def list_spaces(self) -> List[SearchSpace]:
        return list(self._spaces.values())

    def get(self, space_id: str) -> Optional[SearchSpace]:
        return self._spaces.get(space_id)

    def create(self, body: SpaceCreate) -> SearchSpace:
        space = SearchSpace(id=str(uuid.uuid4()), name=body.name, objective=body.objective, params=body.params)
        self._spaces[space.id] = space
        self._save()
        return space


class OptimizerStore:
    def __init__(self, path: str = os.path.join(_DATA_DIR, "optimizations.json")):
        self.path = path
        self._opts: Dict[str, OptimizationStatus] = {}
        if os.path.exists(self.path):
            with open(self.path) as f:
                for item in json.load(f):
                    o = OptimizationStatus(**item)
                    self._opts[o.id] = o

    def _save(self):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, "w") as f:
            json.dump([o.model_dump() for o in self._opts.values()], f, indent=2)

    def get(self, opt_id: str) -> Optional[OptimizationStatus]:
        return self._opts.get(opt_id)

    def list(self) -> List[OptimizationStatus]:
        return list(self._opts.values())

    async def start(self, body: OptimizeRequest) -> OptimizationStatus:
        from training.optimizer import BayesianOptimizer
        space = space_store.get(body.space_id)
        if not space:
            raise ValueError(f"Space {body.space_id} not found")
        opt = OptimizationStatus(
            id=str(uuid.uuid4()),
            space_id=body.space_id,
            status="running",
        )
        self._opts[opt.id] = opt
        self._save()
        asyncio.get_event_loop().create_task(self._run(opt, space, body.n_trials, body.experiment_id))
        return opt

    async def _run(self, opt: OptimizationStatus, space: SearchSpace, n_trials: int, exp_id: Optional[str]):
        from training.optimizer import BayesianOptimizer
        bo = BayesianOptimizer(space.model_dump(), seed=hash(opt.id) % 10_000)
        for i in range(n_trials):
            params = bo.suggest(1)[0]
            trial = OptimizationTrial(trial_id=i, params=params, status="running")
            opt.trials.append(trial)
            score = await self._evaluate(params, exp_id)
            trial.score = score
            trial.status = "completed"
            bo.observe(params, score)
            if opt.status == "running" and len(opt.trials) >= n_trials:
                opt.status = "completed"
                opt.finished_at = time.time()
            best = min((t for t in opt.trials if t.score is not None), key=lambda t: t.score, default=None)
            if best:
                opt.best_score = best.score
                opt.best_params = best.params
            self._save()
            await asyncio.sleep(0.05)

    async def _evaluate(self, params: Dict[str, Any], exp_id: Optional[str]) -> float:
        from training.trainer import Trainer
        from api.schemas import Run, RunCreate, RunStatus
        if exp_id:
            run = run_registry.create(exp_id, RunCreate(name=f"bo_trial", hyperparams=params, config={}))
        else:
            run = Run(id=str(uuid.uuid4()), experiment_id="bo", name="bo_trial", hyperparams=params, config={})
        run.status = RunStatus.running
        trainer = Trainer(run, seed=int(hash(run.id) % 10_000))
        await trainer.train()
        return run.best_metric if run.best_metric is not None else 1.0


space_store = SpaceStore()
optimizer_store = OptimizerStore()
