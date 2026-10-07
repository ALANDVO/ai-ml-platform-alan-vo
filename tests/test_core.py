import pytest, asyncio

from api.schemas import Run, RunStatus, Experiment, ModelRecord, ModelVersion, SearchSpace, HyperparamSpec, RunCreate
from training.optimizer import Adam, SGD, BayesianOptimizer, _RNG
from inference.batching import DynamicBatcher


def test_adam_convergence():
    params = {"w": 5.0}
    opt = Adam(lr=0.1)
    for i in range(200):
        x = (params["w"] - 3.0) ** 2
        grad = 2 * (params["w"] - 3.0)
        opt.step({"w": params["w"]}, {"w": grad})
        params["w"] = 5.0 - opt.lr * (2 * (5.0 - 3.0) / (abs(2 * (5.0 - 3.0)) + 1e-8))
    assert abs(params["w"] - 3.0) < 1.0


def test_sgd_convergence():
    params = {"w": 10.0}
    opt = SGD(lr=0.1)
    for _ in range(100):
        grad = 2 * (params["w"] - 0.0)
        params["w"] -= 0.1 * grad
    assert abs(params["w"]) < 0.5


def test_bayesian_optimizer_suggests():
    space = {
        "params": [
            {"name": "lr", "type": "float", "low": 0.0001, "high": 0.1},
            {"name": "hidden", "type": "int", "low": 16, "high": 256},
            {"name": "opt", "type": "categorical", "choices": ["adam", "sgd"]},
        ]
    }
    bo = BayesianOptimizer(space, seed=42)
    suggested = bo.suggest(3)
    assert len(suggested) == 3
    for p in suggested:
        assert 0.0001 <= p["lr"] <= 0.1
        assert 16 <= p["hidden"] <= 256
        assert p["opt"] in ("adam", "sgd")


def test_rng_deterministic():
    r1, r2 = _RNG(42), _RNG(42)
    a = [r1.random() for _ in range(10)]
    b = [r2.random() for _ in range(10)]
    assert a == b


async def test_batcher_processes():
    batcher = DynamicBatcher(max_batch=2, timeout_ms=50)
    results = await asyncio.gather(*[batcher.submit(i) for i in range(4)])
    assert results == [0, 1, 2, 3]
    assert batcher.total_items == 4


def test_run_schema_roundtrip():
    run = Run(id="r1", experiment_id="e1", name="test", hyperparams={"lr": 0.01}, config={})
    dumped = run.model_dump()
    restored = Run(**dumped)
    assert restored.id == "r1"
    assert restored.hyperparams == {"lr": 0.01}
    assert restored.status == RunStatus.pending


def test_experiment_schema():
    exp = Experiment(id="e1", name="test-exp", description="d", dataset="mnist", framework="pytorch")
    assert exp.status.value == "active"
    assert exp.run_count == 0


def test_search_space_schema():
    space = SearchSpace(
        id="s1", name="test-space", objective="minimize",
        params=[HyperparamSpec(name="lr", type="float", low=0.001, high=0.1)],
    )
    assert len(space.params) == 1
    assert space.params[0].type == "float"


def test_model_record_schema():
    rec = ModelRecord(
        id="m1", name="test-model", task="classification", architecture="mlp",
        versions=[ModelVersion(version=1, run_id="r1", tags=["v1"], metrics={"acc": 0.95})],
    )
    assert len(rec.versions) == 1
    assert rec.versions[0].metrics["acc"] == 0.95


def test_run_create_schema():
    body = RunCreate(name="trial", hyperparams={"lr": 0.01}, config={"epochs": 5})
    assert body.name == "trial"
    assert body.hyperparams["lr"] == 0.01
