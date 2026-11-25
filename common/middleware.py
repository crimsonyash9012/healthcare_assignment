import time
import uuid
import logging
from contextvars import ContextVar

# Context variable for request ID tracking across the execution thread/async context
request_id_ctx: ContextVar[str] = ContextVar('request_id', default='')

logger = logging.getLogger('healthcare.middleware')


def get_current_request_id() -> str:
    """Retrieve the current request ID from context."""
    return request_id_ctx.get()


class RequestIDMiddleware:
    """
    Middleware that assigns a unique Request ID to each incoming request.
    If the client provides an 'X-Request-ID' header, it validates and reuses it;
    otherwise, generates a new UUID4.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        incoming_id = request.headers.get('X-Request-ID')
        if incoming_id and len(incoming_id) <= 64:
            request_id = incoming_id.strip()
        else:
            request_id = str(uuid.uuid4())

        request.request_id = request_id
        token = request_id_ctx.set(request_id)

        try:
            response = self.get_response(request)
        finally:
            request_id_ctx.reset(token)

        response['X-Request-ID'] = request_id
        return response


class RequestLoggingMiddleware:
    """
    Middleware that records structured request execution time, user context,
    HTTP method, status code, and request ID.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start_time = time.perf_counter()
        request_id = getattr(request, 'request_id', 'unknown')

        response = self.get_response(request)

        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        user_id = getattr(request.user, 'id', None) if hasattr(request, 'user') and request.user.is_authenticated else None

        logger.info(
            "Request finished",
            extra={
                'request_id': request_id,
                'method': request.method,
                'path': request.path,
                'status_code': response.status_code,
                'duration_ms': duration_ms,
                'user_id': user_id,
            }
        )

        return response
