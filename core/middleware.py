import time
import logging

logger = logging.getLogger("django")

class RequestLoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start = time.monotonic()
        user = getattr(request, "user", None)
        user_repr = str(user) if user and user.is_authenticated else "anonymous"
        response = self.get_response(request)
        duration_ms = (time.monotonic() - start) * 1000
        logger.info("%s %s | status=%s | user=%s | duration=%.1fms",
            request.method, request.get_full_path(),
            response.status_code, user_repr, duration_ms)
        return response