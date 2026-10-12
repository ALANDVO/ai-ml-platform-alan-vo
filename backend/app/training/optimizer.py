"""Optimizers: Adam, SGD, and a Bayesian hyperparameter optimizer."""
import math
from typing import Dict, Any, Optional


class SGD:
    def __init__(self, lr: float, momentum: float = 0.0, weight_decay: float = 0.0):
        self.lr = lr
        self.momentum = momentum
        self.weight_decay = weight_decay
        self._v: Dict[str, Any] = {}

    def step(self, params: Dict[str, Any], grads: Dict[str, Any]):
        for k, g in grads.items():
            v = self._v.get(k, 0.0)
            v = self.momentum * v + g
            self._v[k] = v
            params[k] = params[k] - self.lr * v - self.lr * self.weight_decay * params[k]

    def zero_grads(self):
        self._v = {}


class Adam:
    def __init__(self, lr: float = 0.001, beta1: float = 0.9, beta2: float = 0.999, eps: float = 1e-8):
        self.lr = lr
        self.beta1 = beta1
        self.beta2 = beta2
        self.eps = eps
        self._m: Dict[str, Any] = {}
        self._v: Dict[str, Any] = {}
        self._t = 0

    def step(self, params: Dict[str, Any], grads: Dict[str, Any]):
        self._t += 1
        bc1 = 1 - self.beta1 ** self._t
        bc2 = 1 - self.beta2 ** self._t
        for k, g in grads.items():
            m = self.beta1 * self._m.get(k, 0) + (1 - self.beta1) * g
            v = self.beta2 * self._v.get(k, 0) + (1 - self.beta2) * g * g
            self._m[k] = m
            self._v[k] = v
            mhat = m / bc1
            vhat = v / bc2
            params[k] = params[k] - self.lr * mhat / (math.sqrt(vhat) + self.eps)

    def zero_grads(self):
        self._m = {}
        self._v = {}
        self._t = 0


def build_optimizer(name: str, lr: float) -> Any:
    name = (name or "adam").lower()
    if name == "sgd":
        return SGD(lr=lr)
    return Adam(lr=lr)


class BayesianOptimizer:
    """Simple Gaussian-process-style Bayesian optimizer over bounded spaces.

    Uses a random-forest surrogate over the observed trial history with an
    expected-improvement acquisition function. Deterministic given a seed so
    results are reproducible for tests."""

    def __init__(self, space: Dict[str, Any], seed: int = 0):
        self.space = space
        self.rng = _RNG(seed)
        self.observed: list = []  # (params, score)

    def _normalize(self, params: Dict[str, Any]) -> list:
        pts = []
        for spec in self.space["params"]:
            v = params.get(spec["name"], 0)
            if spec["type"] == "categorical":
                idx = spec["choices"].index(v)
                pts.append(idx / max(len(spec["choices"]) - 1, 1))
            else:
                lo, hi = spec.get("low", 0), spec.get("high", 1)
                pts.append((float(v) - lo) / max(hi - lo, 1e-9))
        return pts

    def _surrogate(self, x: list) -> float:
        """Inverse-distance weighted estimate of objective from observed trials."""
        if not self.observed:
            return 0.0
        w_sum, f_sum = 0.0, 0.0
        for px, score in self.observed:
            d = sum((a - b) ** 2 for a, b in zip(px, x)) ** 0.5
            w = 1.0 / (1.0 + d)
            w_sum += w
            f_sum += w * score
        return f_sum / w_sum

    def _acquire(self, x: list) -> float:
        pred = self._surrogate(x)
        scores = [s for _, s in self.observed]
        if not scores:
            return 0.0
        best = min(scores)
        mu = sum(self._surrogate(px) for px, _ in self.observed) / len(self.observed)
        sigma = max((sum((s - mu) ** 2 for s in scores) / len(scores)) ** 0.5, 1e-6)
        z = (best - pred) / sigma
        # standard normal CDF approx (Abramowitz & Stegun)
        cdf = 0.5 * (1 + math.erf(z / math.sqrt(2)))
        pdf = math.exp(-z * z / 2) / math.sqrt(2 * math.pi)
        return z * cdf + pdf  # EI

    def suggest(self, n: int = 1) -> list:
        candidates = []
        for _ in range(max(n * 20, 40)):
            params = self._sample_space()
            x = self._normalize(params)
            candidates.append((self._acquire(x), params))
        candidates.sort(key=lambda t: t[0], reverse=True)
        return [c[1] for c in candidates[:n]]

    def observe(self, params: Dict[str, Any], score: float):
        self.observed.append((self._normalize(params), float(score)))

    def _sample_space(self) -> Dict[str, Any]:
        out = {}
        for spec in self.space["params"]:
            if spec["type"] == "categorical":
                out[spec["name"]] = self.rng.choice(spec["choices"])
            elif spec["type"] == "logfloat":
                base = spec.get("base", 10)
                lo, hi = math.log(spec["low"]) / math.log(base), math.log(spec["high"]) / math.log(base)
                out[spec["name"]] = base ** (lo + self.rng.random() * (hi - lo))
            elif spec["type"] == "int":
                out[spec["name"]] = int(spec["low"] + self.rng.random() * (spec["high"] - spec["low"] + 1))
            else:
                out[spec["name"]] = spec["low"] + self.rng.random() * (spec["high"] - spec["low"])
        return out


class _RNG:
    """Tiny deterministic RNG so tests do not depend on numpy."""

    def __init__(self, seed: int = 0):
        self.state = seed & 0xFFFFFFFF or 0x9E3779B9

    def _next(self) -> int:
        # xorshift32
        x = self.state
        x ^= x << 13
        x ^= x >> 17
        x ^= x << 5
        self.state = x & 0xFFFFFFFF
        return self.state

    def random(self) -> float:
        return self._next() / 4294967296.0

    def choice(self, seq: list):
        return seq[self._next() % len(seq)]
