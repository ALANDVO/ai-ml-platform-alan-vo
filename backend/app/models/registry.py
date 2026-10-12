"""Model registry with versioning, tags, and A/B comparison."""
import os, json, time, uuid, logging
from typing import List, Optional, Dict, Any

from api.schemas import ModelRecord, ModelRegister, ModelVersion

logger = logging.getLogger(__name__)


class ModelRegistry:
    def __init__(self, storage_dir: str = "data/models.json"):
        self.storage_path = storage_dir
        self._models: Dict[str, ModelRecord] = {}

    def ensure_storage(self):
        os.makedirs(os.path.dirname(self.storage_path) or ".", exist_ok=True)
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path) as f:
                    raw = json.load(f)
                for item in raw:
                    rec = ModelRecord(**item)
                    self._models[rec.id] = rec
            except (json.JSONDecodeError, ValueError):
                logger.warning("Model registry storage unreadable; starting fresh")
        else:
            self._persist()

    def _persist(self):
        os.makedirs(os.path.dirname(self.storage_path) or ".", exist_ok=True)
        with open(self.storage_path, "w") as f:
            json.dump([m.model_dump() for m in self._models.values()], f, indent=2)

    def all(self) -> List[ModelRecord]:
        return list(self._models.values())

    def get(self, model_id: str) -> Optional[ModelRecord]:
        return self._models.get(model_id)

    def register(self, body: ModelRegister) -> ModelRecord:
        from experiments.tracking import run_registry
        run = run_registry.get(body.run_id)
        if not run:
            raise ValueError(f"Run {body.run_id} not found")
        model_id = f"m_{body.name.lower().replace(' ', '_')}_{uuid.uuid4().hex[:6]}"
        metrics = {**run.metrics_summary(), **body.metrics}
        version = ModelVersion(
            version=1,
            run_id=run.id,
            tags=body.tags,
            metrics=metrics,
        )
        record = ModelRecord(
            id=model_id,
            name=body.name,
            description=body.description,
            task=body.task,
            architecture=body.architecture,
            versions=[version],
        )
        self._models[model_id] = record
        self._persist()
        logger.info("Registered model %s (v1) from run %s", model_id, run.id)
        return record

    def add_version(self, model_id: str, run_id: str, tags: List[str], metrics: Dict[str, float], parent: Optional[int] = None) -> ModelRecord:
        record = self._models.get(model_id)
        if not record:
            raise KeyError(model_id)
        next_v = max((v.version for v in record.versions), default=0) + 1
        record.versions.append(ModelVersion(
            version=next_v, run_id=run_id, tags=tags, metrics=metrics, parent_version=parent,
        ))
        self._persist()
        return record


model_registry = ModelRegistry(storage_dir=os.path.join(os.path.dirname(__file__), "..", "data", "models.json"))
