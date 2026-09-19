"""Cyber Fraud Correlator FastAPI Application.

Assembles correlation, risk scoring, evidentiary custody integrity verification,
and court-ready brief generation into a unified REST API service.
"""

import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1 import api_router
from app.core.config import settings
from app.db.session import engine, init_db
from app.services.ingestion.exceptions import IngestionError

# Configure structured logging format
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
)
logger = logging.getLogger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context: initialize database schema on startup."""
    logger.info("Initializing database schema...")
    init_db(engine)
    logger.info("Database schema initialized successfully.")
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    description=(
        "AI-powered cyber fraud artifact correlator and risk intelligence engine "
        "tailored for law enforcement and financial intelligence investigations."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# CORS Middleware
# ---------------------------------------------------------------------------
allowed_origins = [
    f"http://localhost:{settings.FRONTEND_PORT}",
    f"http://127.0.0.1:{settings.FRONTEND_PORT}",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Structured Request Logging & Request-ID Middleware
# ---------------------------------------------------------------------------
@app.middleware("http")
async def structured_logging_middleware(request: Request, call_next):
    """Assign unique request ID, time execution, and structure logs."""
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    request.state.request_id = request_id

    client_host = request.client.host if request.client else "unknown"
    start_time = time.perf_counter()

    logger.info(
        "--> [req=%s] %s %s (client=%s)",
        request_id,
        request.method,
        request.url.path,
        client_host,
    )

    try:
        response = await call_next(request)
    except Exception as exc:
        duration_ms = (time.perf_counter() - start_time) * 1000.0
        logger.error(
            "<-- [req=%s] %s %s ERROR after %.2fms: %s",
            request_id,
            request.method,
            request.url.path,
            duration_ms,
            exc,
        )
        raise exc

    duration_ms = (time.perf_counter() - start_time) * 1000.0
    response.headers["X-Request-ID"] = request_id

    logger.info(
        "<-- [req=%s] %s %s status=%d completed_in=%.2fms",
        request_id,
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )
    return response


# ---------------------------------------------------------------------------
# Global Exception Handlers (Clean JSON error responses, zero stack-trace leak)
# ---------------------------------------------------------------------------
@app.exception_handler(IngestionError)
async def ingestion_error_handler(
    request: Request, exc: IngestionError
) -> JSONResponse:
    """Transform custom evidentiary ingestion errors into clean JSON responses."""
    request_id = getattr(request.state, "request_id", "unknown")
    logger.warning("Ingestion error [req=%s]: %s", request_id, exc)
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": exc.__class__.__name__,
            "detail": str(exc),
            "request_id": request_id,
        },
        headers={"X-Request-ID": request_id},
    )


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
    """Handle domain validation errors gracefully."""
    request_id = getattr(request.state, "request_id", "unknown")
    logger.warning("Validation error [req=%s]: %s", request_id, exc)
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": "ValueError",
            "detail": str(exc),
            "request_id": request_id,
        },
        headers={"X-Request-ID": request_id},
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch unhandled internal errors without leaking raw tracebacks to the client."""
    request_id = getattr(request.state, "request_id", "unknown")
    # Preserve default FastAPI HTTPException handling
    if isinstance(exc, HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail, "request_id": request_id},
            headers={"X-Request-ID": request_id},
        )

    logger.error("Unhandled exception [req=%s]: %s", request_id, exc, exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "InternalServerError",
            "detail": (
                "An internal server error occurred. "
                "Please contact the administrator."
            ),
            "request_id": request_id,
        },
        headers={"X-Request-ID": request_id},
    )


# ---------------------------------------------------------------------------
# Routers (Mounted under both /api/v1 and root /)
# ---------------------------------------------------------------------------
app.include_router(api_router, prefix="/api/v1")
app.include_router(api_router)


# ---------------------------------------------------------------------------
# System Endpoints
# ---------------------------------------------------------------------------
@app.get("/health", tags=["system"], summary="Service health check")
async def health_check() -> dict[str, str]:
    """Health check confirming API service status and phase readiness."""
    return {
        "status": "ok",
        "phase": "Phase 6 - Brief Generation & API Complete",
        "service": settings.PROJECT_NAME,
    }
