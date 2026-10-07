import time, logging
from collections import defaultdict
from fastapi import Request, Response

logger = logging.getLogger("api.middleware")

class RateLimiter:
    def __init__(self, max_requests: int = 300, window_s: int = 60):
        self.max_requests = max_requests
        self.window_s = window_s
        self.hits: dict = defaultdict(list)

    def allow(self, key: str) -> bool:
        now = time.time()
        cutoff = now - self.window_s
        self.hits[key] = [t for t in self.hits[key] if t > cutoff]
        if len(self.hits[key]) >= self.max_requests:
            return False
        self.hits[key].append(now)
        return True

_limiter = RateLimiter(max_requests=int(os.environ.get("RATE_LIMIT", "300")))

def rate_limiter(request: Request, call_next):
    key = request.client.host if request.client else "unknown"
    if not _limiter.allow(key):
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded"})
    return call_next(request)

def request_logger(request: Request, call_next):
    start = time.perf_counter()
    response = call_next(request)
    elapsed = (time.perf_counter() - start) * 1000
    logger.info("%s %s → %d (%.1fms)", request.method, request.url.path, response.status_code, elapsed)
    response.headers["X-Process-Time-Ms"] = f"{elapsed:.1f}"
    return response
