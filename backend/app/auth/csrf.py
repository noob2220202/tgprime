from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

_SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


class RequireRequestedWithMiddleware(BaseHTTPMiddleware):
    """Lightweight CSRF mitigation: state-changing requests must carry a custom header,
    which a cross-site <form> submission cannot set. Cheap insurance on top of SameSite=Lax cookies.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if (
            request.method not in _SAFE_METHODS
            and request.url.path.startswith("/api/")
            and request.headers.get("x-requested-with") != "XMLHttpRequest"
        ):
            return Response(status_code=403, content="Missing X-Requested-With header")
        return await call_next(request)
