"""Callback system: metric tracking, early stopping, best-model saving."""
import time, logging, os
from typing import Callable, Dict, Any, List

logger = logging.getLogger(__name__)


class Callback:
    name = "base"

    def on_train_start(self, run): ...   # noqa: B027
    def on_epoch_end(self, run, epoch: int, metrics: Dict[str, float]): ...  # noqa: B027
    def on_train_end(self, run): ...     # noqa: B027


class MetricTracker(Callback):
    name = "metric_tracker"

    def __init__(self, interval: int = 1):
        self.interval = interval
        self.last_log = 0

    def on_epoch_end(self, run, epoch: int, metrics: Dict[str, float]):
        if epoch - self.last_log >= self.interval:
            parts = " ".join(f"{k}={v:.4f}" for k, v in metrics.items())
            logger.info("run=%s epoch=%d %s", run.id, epoch, parts)
            self.last_log = epoch


class EarlyStopping(Callback):
    name = "early_stopping"

    def __init__(self, patience: int = 5, monitor: str = "loss", min_delta: float = 1e-4):
        self.patience = patience
        self.monitor = monitor
        self.min_delta = min_delta
        self.best = float("inf")
        self.counter = 0

    def on_epoch_end(self, run, epoch: int, metrics: Dict[str, float]):
        val = metrics.get(self.monitor)
        if val is None:
            return
        if val < self.best - self.min_delta:
            self.best = val
            self.counter = 0
        else:
            self.counter += 1
        if self.counter >= self.patience:
            run_registry_stop(run.id)


def run_registry_stop(run_id: str):
    """Defer import to avoid cycles; training.trainer imports this module."""
    from training.trainer import training_pool
    training_pool.stop(run_id)


class BestModelSave(Callback):
    name = "best_model_save"

    def __init__(self, save_dir: str = "checkpoints"):
        self.save_dir = save_dir
        self.best = float("inf")
        self.best_epoch = 0

    def on_epoch_end(self, run, epoch: int, metrics: Dict[str, float]):
        val = metrics.get("loss", float("inf"))
        if val < self.best:
            self.best = val
            self.best_epoch = epoch

    def on_train_end(self, run):
        os.makedirs(self.save_dir, exist_ok=True)
        path = os.path.join(self.save_dir, f"{run.id}_best.pt.json")
        import json
        with open(path, "w") as f:
            json.dump({
                "run_id": run.id,
                "best_epoch": self.best_epoch,
                "best_loss": self.best,
                "hyperparams": run.hyperparams,
                "saved_at": time.time(),
            }, f, indent=2)
        logger.info("Saved best model checkpoint for run %s → %s", run.id, path)


class CallbackList:
    def __init__(self):
        self.callbacks: List[Callback] = []

    def add(self, cb: Callback):
        self.callbacks.append(cb)

    def on_train_start(self, run):
        for cb in self.callbacks:
            cb.on_train_start(run)

    def on_epoch_end(self, run, epoch: int, metrics: Dict[str, float]):
        for cb in self.callbacks:
            cb.on_epoch_end(run, epoch, metrics)

    def on_train_end(self, run):
        for cb in self.callbacks:
            cb.on_train_end(run)
