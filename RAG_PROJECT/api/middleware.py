import uuid
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from utils.log_utils import log, request_id_var


class RequestTracingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        token = request_id_var.set(request_id)

        start = time.perf_counter()
        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            return response
        except Exception:
            elapsed_ms = (time.perf_counter() - start) * 1000
            log.error(
                f"method={request.method} path={request.url.path} "
                f"duration_ms={elapsed_ms:.1f} "
                f"request_id={request_id}"
            )
            raise
        finally:
            request_id_var.reset(token)
