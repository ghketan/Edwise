import os
import re
import uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from backend.app.api.v1.api import api_router
from backend.app.core.config import settings
from backend.app.core.database import Base, engine
from backend.app.core.exceptions import EdwiseException
from backend.app.core.logging import logger, request_id_ctx, setup_logging, user_id_ctx


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Setup structured logging
    setup_logging()
    logger.info("Initializing EDWISE API application...")

    # Create tables
    Base.metadata.create_all(bind=engine)
    try:
        with engine.begin() as conn:
            from sqlalchemy import text
            res = conn.execute(text("PRAGMA table_info(submissions)")).fetchall()
            cols = [r[1] for r in res]
            if cols and "attachment_url" not in cols:
                conn.execute(text("ALTER TABLE submissions ADD COLUMN attachment_url VARCHAR(500)"))

            res_exams = conn.execute(text("PRAGMA table_info(exams)")).fetchall()
            exam_cols = [r[1] for r in res_exams]
            if exam_cols and "time_slot" not in exam_cols:
                conn.execute(text("ALTER TABLE exams ADD COLUMN time_slot VARCHAR(50) DEFAULT '09:00 AM - 12:00 PM'"))
            if exam_cols and "datesheet_filename" not in exam_cols:
                conn.execute(text("ALTER TABLE exams ADD COLUMN datesheet_filename VARCHAR(255)"))
    except Exception as e:
        logger.debug(f"SQLite column migration check skipped: {e}")
    logger.info("Database tables initialized.")

    yield

    logger.info("Shutting down EDWISE API application...")


is_prod = settings.ENVIRONMENT.lower() == "production"

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Backend API for the EDWISE Learning Analytics Platform",
    lifespan=lifespan,
    docs_url=None if is_prod else "/docs",
    redoc_url=None if is_prod else "/redoc",
    openapi_url=None if is_prod else "/openapi.json"
)

# Assemble CORS origins from BACKEND_CORS_ORIGINS and ALLOWED_ORIGINS
cors_origins = list(settings.BACKEND_CORS_ORIGINS)
if settings.ALLOWED_ORIGINS:
    for o in settings.ALLOWED_ORIGINS.split(","):
        clean_o = o.strip()
        if clean_o and clean_o not in cors_origins:
            cors_origins.append(clean_o)

# CORS Middleware with automatic Cloudflare Pages regex matching
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_origin_regex=r"^https:\/\/.*\.pages\.dev$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

REQUEST_ID_REGEX = re.compile(r"^[a-zA-Z0-9\-_]{1,64}$")


# Structured Request ID Middleware (D-014, R-017, H-01)
@app.middleware("http")
async def logging_and_request_id_middleware(request: Request, call_next):
    raw_id = request.headers.get("X-Request-ID", "")
    if raw_id and REQUEST_ID_REGEX.match(raw_id):
        req_id = raw_id
    else:
        req_id = str(uuid.uuid4())

    token_req = request_id_ctx.set(req_id)
    token_user = user_id_ctx.set(None)

    logger.info(f"Incoming request: {request.method} {request.url.path}")
    try:
        response = await call_next(request)
        # Check if user_id was set on request state by auth dependency (H-01)
        if hasattr(request.state, "user_id"):
            user_id_ctx.set(request.state.user_id)
        response.headers["X-Request-ID"] = req_id
        return response
    except Exception as e:
        logger.error(f"Unhandled error processing request: {request.method} {request.url.path}", exc_info=False)
        # R-017: Never leak internal SQL parameters, tracebacks, or student PII to client
        return JSONResponse(
            status_code=500,
            content={"detail": "An internal server error occurred. Please contact the administrator."},
            headers={"X-Request-ID": req_id}
        )
    finally:
        request_id_ctx.reset(token_req)
        user_id_ctx.reset(token_user)


# Request Validation Error Handler (stripping sensitive 'input' fields per R-017)
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = []
    for err in exc.errors():
        clean_err = {
            "type": err.get("type"),
            "loc": err.get("loc"),
            "msg": err.get("msg")
        }
        errors.append(clean_err)

    return JSONResponse(
        status_code=422,
        content={"detail": errors},
        headers={"X-Request-ID": request_id_ctx.get() or ""}
    )


# Custom Application Exception Handler
@app.exception_handler(EdwiseException)
async def edwise_exception_handler(request: Request, exc: EdwiseException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers={"X-Request-ID": request_id_ctx.get() or ""}
    )


# Note: /uploads is NOT mounted as StaticFiles to prevent unauthenticated direct file enumeration.
# All downloads (datesheets, assignment submissions) are strictly routed through authenticated,
# scoped endpoints: /api/v1/exams/{id}/datesheet and /api/v1/assignments/files/{filename}.
uploads_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "backend", "uploads")
os.makedirs(uploads_dir, exist_ok=True)

# Include API v1 Router
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/health", tags=["System"])
def health_check():
    return {
        "status": "ok",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT
    }


@app.get("/", tags=["System"])
def root():
    return {
        "message": "Welcome to EDWISE Learning Analytics Platform API",
        "version": settings.VERSION,
        "docs_url": "/docs" if not is_prod else "Disabled in production"
    }
