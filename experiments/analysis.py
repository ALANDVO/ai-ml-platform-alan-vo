"""LLM-powered experiment comparison, architecture suggestions, and analysis."""
import json, logging
from typing import List, Optional, Dict, Any

import httpx

from api.schemas import ArchitectureRequest, AnalyzeRequest
from config import settings

logger = logging.getLogger(__name__)


class LLMClient:
    def __init__(self):
        self.api_key = settings.llm_api_key
        self.base_url = settings.llm_base_url.rstrip("/")
        self.model = settings.llm_model

    async def chat(self, system: str, user: str, temperature: float = 0.3, max_tokens: int = 1500) -> str:
        if not self.api_key:
            return json.dumps({"note": "LLM_API_KEY not set — returning heuristic result"})
        url = f"{self.base_url}/chat/completions"
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]


_llm = LLMClient()


class LLMArchitect:
    """Suggests model architectures based on task, dataset size, and constraints."""

    async def suggest(self, req: ArchitectureRequest) -> Dict[str, Any]:
        system = ("You are an ML architect. Recommend a model architecture, "
                  "hyperparameter ranges, and training strategy for the given task. "
                  "Respond with valid JSON only.")
        user = (f"Task: {req.task}\n"
                f"Dataset size: {req.dataset_size} samples\n"
                f"Feature dimensionality: {req.features}\n"
                f"Constraints: {req.constraints or 'none'}\n\n"
                f"Respond with JSON: {{architecture, layers, activation, optimizer, lr_range, batch_range, notes}}")
        raw = await _llm.chat(system, user)
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return self._heuristic(req)

    def _heuristic(self, req: ArchitectureRequest) -> Dict[str, Any]:
        if req.dataset_size < 10_000:
            arch, layers = "mlp", 2
        elif req.dataset_size < 1_000_000:
            arch, layers = "mlp_deep", 4
        else:
            arch, layers = "transformer", 6
        return {
            "architecture": arch,
            "layers": layers,
            "activation": "gelu" if layers > 2 else "relu",
            "optimizer": "adam",
            "lr_range": [1e-4, 3e-3],
            "batch_range": [32, 256],
            "notes": f"Heuristic suggestion for {req.task} with {req.dataset_size} samples",
        }


class LLMAnalyst:
    """Compares experiments and generates insights."""

    async def analyze(self, req: AnalyzeRequest) -> Dict[str, Any]:
        from experiments.tracking import run_registry, experiment_store
        exps = []
        for eid in req.experiment_ids:
            exp = experiment_store.get(eid)
            if not exp:
                continue
            runs = run_registry.list_for_experiment(eid)
            exps.append({
                "id": exp.id,
                "name": exp.name,
                "runs": [
                    {"id": r.id, "name": r.name, "status": r.status.value,
                     "best_metric": r.best_metric, "hyperparams": r.hyperparams}
                    for r in runs
                ],
            })
        if not exps:
            return {"insights": "No experiments found for the given IDs", "experiments": []}
        system = ("You are an ML experiment analyst. Compare the given experiments "
                  "and provide actionable insights. Respond with valid JSON only.")
        user = (f"Experiments: {json.dumps(exps, indent=2)}\n"
                f"Focus: {req.focus}\n\n"
                f"Respond with JSON: {{summary, best_experiment, key_findings, recommendations, risks}}")
        raw = await _llm.chat(system, user, max_tokens=2000)
        try:
            out = json.loads(raw)
            out["experiments"] = exps
            return out
        except json.JSONDecodeError:
            best = max((e for e in exps if e["runs"]), key=lambda e: max((r.get("best_metric") or 999) for r in e["runs"]), default=None)
            return {
                "summary": f"Analyzed {len(exps)} experiments; best is {best['name'] if best else 'none'}",
                "best_experiment": best["id"] if best else None,
                "key_findings": [f"{e['name']} has {len(e['runs'])} runs" for e in exps],
                "recommendations": ["Increase epochs for underfitting runs"],
                "risks": ["Small dataset may cause overfitting"],
                "experiments": exps,
            }


llm_architect = LLMArchitect()
llm_analyst = LLMAnalyst()
