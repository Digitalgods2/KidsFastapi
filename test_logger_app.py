from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.middleware.base import BaseHTTPMiddleware
from importlib.machinery import SourceFileLoader

logger_mod = SourceFileLoader('kk_logger','services/logger.py').load_module()
get_logger = logger_mod.get_logger
set_request_id = logger_mod.set_request_id
reset_request_id = logger_mod.reset_request_id

class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        rid = request.headers.get("X-Request-ID") or "RIDTEST"
        token = set_request_id(rid)
        try:
            response = await call_next(request)
        finally:
            reset_request_id(token)
        response.headers["X-Request-ID"] = rid
        return response

async def homepage(request):
    log = get_logger("database")
    log.info("test_db_log", extra={"component": "database", "endpoint": "/"})
    return JSONResponse({"ok": True})

app = Starlette(routes=[Route("/", homepage)])
app.add_middleware(RequestIdMiddleware)
