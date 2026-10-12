"""Training loop with checkpointing, early stopping, and async run management."""
import asyncio, time, uuid, logging
from typing import Optional, Dict, Any, List

import numpy as np

from api.schemas import Run, RunStatus, RunCreate, MetricPoint
from config import settings
from training.callbacks import CallbackList
from training.optimizer import Adam, SGD, build_optimizer

logger = logging.getLogger(__name__)

class Trainer:
    """Runs a training loop over synthetic or in-memory datasets with full
    metric tracking, checkpointing, and early stopping via the callback system."""

    def __init__(self, run: Run, seed: int = 42):
        self.run = run
        self.rng = np.random.default_rng(seed)
        self.stop_flag = False
        self.callbacks = CallbackList()
        self._optimizer: Optional[Any] = None

    def _make_model(self):
        hp = self.run.hyperparams
        hidden = int(hp.get("hidden_units", 64))
        n_classes = int(hp.get("n_classes", 10))
        in_dim = int(hp.get("input_dim", 32))
        w1 = self.rng.normal(0, 0.5, (in_dim, hidden)).astype(np.float64)
        b1 = np.zeros(hidden)
        w2 = self.rng.normal(0, 0.5, (hidden, n_classes)).astype(np.float64)
        b2 = np.zeros(n_classes)
        return {"w1": w1, "b1": b1, "w2": w2, "b2": b2}

    def _forward(self, params: Dict[str, Any], x: np.ndarray) -> np.ndarray:
        h = x @ params["w1"] + params["b1"]
        h = np.tanh(h)
        return h @ params["w2"] + params["b2"]

    def _loss_accuracy(self, params: Dict[str, Any], x: np.ndarray, y: np.ndarray):
        h = x @ params["w1"] + params["b1"]
        hidden_act = np.tanh(h)
        logits = hidden_act @ params["w2"] + params["b2"]
        exp = np.exp(logits - logits.max(axis=1, keepdims=True))
        probs = exp / exp.sum(axis=1, keepdims=True)
        log_probs = np.log(probs + 1e-12)
        loss = -log_probs[np.arange(len(y)), y].mean()
        acc = (logits.argmax(axis=1) == y).mean()
        dsm = probs.copy()
        dsm[np.arange(len(y)), y] -= 1.0
        dsm /= len(y)
        gw2 = hidden_act.T @ dsm
        gb2 = dsm.sum(axis=0)
        dh = dsm @ params["w2"].T
        dh = dh * (1 - h ** 2)
        gw1 = x.T @ dh
        gb1 = dh.sum(axis=0)
        return float(loss), float(acc), {"w1": gw1, "b1": gb1, "w2": gw2, "b2": gb2}

    async def train(self):
        hp = self.run.hyperparams
        epochs = int(hp.get("epochs", 20))
        lr = float(hp.get("learning_rate", 0.01))
        batch = int(hp.get("batch_size", 32))
        patience = int(hp.get("early_stop_patience", 5))
        in_dim = int(hp.get("input_dim", 32))
        n_classes = int(hp.get("n_classes", 10))
        n_samples = int(hp.get("n_samples", 512))

        x = self.rng.normal(0, 1, (n_samples, in_dim))
        y = self.rng.integers(0, n_classes, n_samples)
        self._optimizer = build_optimizer(hp.get("optimizer", "adam"), lr)

        params = self._make_model()
        best_loss = float("inf")
        best_epoch = 0
        no_improve = 0

        self.run.status = RunStatus.running
        self.run.started_at = time.time()
        self.callbacks.on_train_start(self.run)

        for epoch in range(epochs):
            if self.stop_flag:
                break
            idx = self.rng.permutation(n_samples)
            epoch_loss, epoch_acc = 0.0, 0.0
            for start in range(0, n_samples, batch):
                if self.stop_flag:
                    break
                i = idx[start:start + batch]
                xb, yb = x[i], y[i]
                loss, acc, grads = self._loss_accuracy(params, xb, yb)
                self._optimizer.step(params, grads)
                epoch_loss += loss * len(i)
                epoch_acc += acc * len(i)
            epoch_loss /= n_samples
            epoch_acc /= n_samples

            self.run.metrics.setdefault("loss", []).append(MetricPoint(step=epoch, value=epoch_loss))
            self.run.metrics.setdefault("accuracy", []).append(MetricPoint(step=epoch, value=epoch_acc))
            self.callbacks.on_epoch_end(self.run, epoch, {"loss": epoch_loss, "accuracy": epoch_acc})

            if epoch_loss < best_loss - 1e-4:
                best_loss = epoch_loss
                best_epoch = epoch
                no_improve = 0
            else:
                no_improve += 1
            if patience and no_improve >= patience:
                logger.info("Run %s: early stopping at epoch %d", self.run.id, epoch)
                break

        if self.stop_flag:
            self.run.status = RunStatus.stopped
        else:
            self.run.status = RunStatus.completed
        self.run.finished_at = time.time()
        self.run.best_metric = best_loss
        self.run.best_metric_name = "loss"
        self.callbacks.on_train_end(self.run)
        return self.run


class TrainingPool:
    """Manages concurrent training runs with a bounded semaphore."""

    def __init__(self, max_concurrent: int = 2):
        self.max_concurrent = max_concurrent
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._runs: Dict[str, Run] = {}
        self._tasks: Dict[str, asyncio.Task] = {}

    async def start_run(self, experiment_id: str, body: RunCreate) -> Run:
        from experiments.tracking import run_registry
        if not run_registry.experiment_exists(experiment_id):
            raise ValueError("Experiment not found")
        run = run_registry.create(experiment_id, body)
        trainer = Trainer(run, seed=int(hash(run.id) % 10_000))
        async def _job():
            async with self._semaphore:
                try:
                    await trainer.train()
                except Exception:
                    run.status = RunStatus.failed
                    logger.exception("Run %s failed", run.id)
        self._runs[run.id] = run
        self._tasks[run.id] = asyncio.create_task(_job())
        return run

    def stop(self, run_id: str):
        from experiments.tracking import run_registry
        run = run_registry.get(run_id)
        if run and run.status == RunStatus.running:
            run_registry.stop(run_id)

    def active_jobs(self) -> List[Dict[str, Any]]:
        from experiments.tracking import run_registry
        from api.schemas import TrainingJob
        jobs = []
        for run in run_registry.all():
            if run.status != RunStatus.running:
                continue
            loss_pts = run.metrics.get("loss", [])
            acc_pts = run.metrics.get("accuracy", [])
            step = loss_pts[-1].step if loss_pts else 0
            jobs.append(TrainingJob(
                run_id=run.id, name=run.name, experiment_id=run.experiment_id,
                status=run.status.value, step=step,
                loss=loss_pts[-1].value if loss_pts else None,
                accuracy=acc_pts[-1].value if acc_pts else None,
                progress=min(step / max(step + 1, 1), 1.0),
            ))
        return jobs

training_pool = TrainingPool(max_concurrent=settings.max_concurrent_runs)
