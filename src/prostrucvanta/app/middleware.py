import re
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

def normalize_base_path(value: str) -> str:
    value = (value or "").strip()
    if not value or value == "/":
        return ""
    return "/" + value.strip("/")

class SubpathMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, prefix: str = ""):
        super().__init__(app)
        self.prefix = normalize_base_path(prefix)

    async def dispatch(self, request: Request, call_next):
        if not self.prefix:
            return await call_next(request)
        path = request.scope.get("path", "")
        # Adjust path for internal routing
        if path == self.prefix:
            request.scope["path"] = "/"
            request.scope["root_path"] = request.scope.get("root_path", "") + self.prefix
        elif path.startswith(self.prefix + "/"):
            request.scope["path"] = path[len(self.prefix):]
            request.scope["root_path"] = request.scope.get("root_path", "") + self.prefix
        else:
            return Response("Not Found", status_code=404)
        response = await call_next(request)
        return response


class RedirectPrefixMiddleware(BaseHTTPMiddleware):
    """Keep absolute-path redirects inside the host's mounted app prefix."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        location = response.headers.get("location")
        root_path = request.scope.get("root_path", "").rstrip("/")
        if location and location.startswith("/") and root_path:
            if location != root_path and not location.startswith(root_path + "/"):
                response.headers["location"] = root_path + location
        return response
