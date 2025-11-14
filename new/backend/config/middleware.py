import time
from typing import Callable


class RequestTimingMiddleware:
    def __init__(self, get_response: Callable):
        self.get_response = get_response

    def __call__(self, request):
        start = time.perf_counter()
        response = self.get_response(request)
        duration_ms = int((time.perf_counter() - start) * 1000)
        try:
            response["X-Request-Duration"] = str(duration_ms)
        except Exception:
            pass
        return response


