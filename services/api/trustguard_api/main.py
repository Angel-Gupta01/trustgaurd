# services/api/trustguard_api/main.py
import uuid
import time
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError

from trustguard_api.core.config import settings
from trustguard_api.core.exceptions import AppError
from trustguard_api.core.envelope import build_envelope_response
from trustguard_api.modules.shared.schemas import ApiError

from trustguard_api.modules.auth.router import router as auth_router
from trustguard_api.modules.vishing.router import router as vishing_router
from trustguard_api.modules.deepfake.router import router as deepfake_router
from trustguard_api.modules.provenance.router import router as provenance_router
from trustguard_api.modules.incidents.router import router as incidents_router
from trustguard_api.modules.admin.router import router as admin_router
from trustguard_api.modules.realtime.router import router as ws_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request-ID & Response Timing Middleware
@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
    req_id = request.headers.get("X-Request-Id", str(uuid.uuid4()))
    request.state.request_id = req_id
    start_time = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start_time) * 1000
    response.headers["X-Request-Id"] = req_id
    response.headers["X-Response-Time-Ms"] = f"{duration_ms:.2f}"
    return response

# Standard Exception Handler for Domain Errors
@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    error_dto = ApiError(code=exc.code, message=exc.message, field=exc.field)
    return build_envelope_response(
        error=error_dto,
        request_id=getattr(request.state, "request_id", str(uuid.uuid4())),
        status_code=exc.http_status,
    )

# Standard Validation Error Handler
@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    first_error = exc.errors()[0] if exc.errors() else {}
    field = ".".join(str(loc) for loc in first_error.get("loc", [])) if "loc" in first_error else None
    error_dto = ApiError(
        code="VALIDATION_ERROR",
        message=first_error.get("msg", "Invalid request body"),
        field=field,
    )
    return build_envelope_response(
        error=error_dto,
        request_id=getattr(request.state, "request_id", str(uuid.uuid4())),
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
    )

# Routers Mounting
app.include_router(auth_router, prefix=settings.API_V1_PREFIX)
app.include_router(vishing_router, prefix=settings.API_V1_PREFIX)
app.include_router(deepfake_router, prefix=settings.API_V1_PREFIX)
app.include_router(provenance_router, prefix=settings.API_V1_PREFIX)
app.include_router(incidents_router, prefix=settings.API_V1_PREFIX)
app.include_router(admin_router, prefix=settings.API_V1_PREFIX)
app.include_router(ws_router, prefix=settings.API_V1_PREFIX)

@app.get("/health", tags=["Health"])
async def health_check(request: Request):
    return build_envelope_response(
        data={"status": "healthy", "service": "trustguard-api", "version": settings.VERSION},
        request_id=getattr(request.state, "request_id", str(uuid.uuid4())),
    )
