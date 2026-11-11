import time
import uuid
import logging
from typing import Callable
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("app.access")

# Sensitive header names to mask in audit logs
SENSITIVE_HEADERS = {
    "authorization",
    "cookie",
    "set-cookie",
    "x-api-key",
    "api-key",
    "token",
}


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware that records HTTP request metrics, assigns correlation IDs,
    and logs access patterns without exposing passwords, JWTs, or API secrets.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 1. Establish or propagate Request ID
        request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
        request.state.request_id = request_id

        start_time = time.perf_counter()

        # 2. Process Request
        try:
            response: Response = await call_next(request)
        except Exception:
            # Let the exception handler deal with the response, but record elapsed time
            process_time_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.error(
                f"REQUEST_FAILED: req_id={request_id} method={request.method} "
                f"path={request.url.path} elapsed={process_time_ms}ms"
            )
            raise

        process_time_ms = round((time.perf_counter() - start_time) * 1000, 2)

        # 3. Attach Request-ID and Timing Headers to Response
        response.headers["x-request-id"] = request_id
        response.headers["x-process-time-ms"] = str(process_time_ms)

        # 4. Safe Logging (Exclude passwords and sensitive tokens)
        client_ip = request.client.host if request.client else "unknown"
        logger.info(
            f"req_id={request_id} client={client_ip} method={request.method} "
            f"path={request.url.path} status={response.status_code} elapsed={process_time_ms}ms"
        )

        return response
