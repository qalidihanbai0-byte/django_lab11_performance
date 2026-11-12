import logging
import time

from django.db import connection
from django.test.utils import CaptureQueriesContext


logger = logging.getLogger("perf")


class TimingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        started_at = time.perf_counter()
        with CaptureQueriesContext(connection) as queries:
            response = self.get_response(request)
        elapsed_ms = (time.perf_counter() - started_at) * 1000
        level = logging.WARNING if elapsed_ms > 300 else logging.INFO
        logger.log(
            level,
            "%s %s duration_ms=%.3f sql_queries=%d",
            request.method,
            request.get_full_path(),
            elapsed_ms,
            len(queries),
        )
        return response
