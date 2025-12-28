from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import get_settings
from app.api.dependencies import get_database, get_embedding_queue
from app.api.routes import health, users, notebooks, documents, search, queue


class APIKeyMiddleware(BaseHTTPMiddleware):
    """Middleware to validate API key on all requests."""

    # Paths that don't require authentication
    PUBLIC_PATHS = {"/", "/docs", "/redoc", "/openapi.json", "/api/v1/health"}

    async def dispatch(self, request: Request, call_next):
        settings = get_settings()

        # Skip auth if no API key is configured
        if not settings.api_key:
            return await call_next(request)

        # Skip auth for public paths and OPTIONS requests
        if request.url.path in self.PUBLIC_PATHS or request.method == "OPTIONS":
            return await call_next(request)

        # Check API key
        api_key = request.headers.get("X-API-Key") or request.query_params.get("api_key")

        if not api_key:
            return JSONResponse(
                status_code=401,
                content={"detail": "Missing API key. Provide X-API-Key header or api_key query param."}
            )

        if api_key != settings.api_key:
            return JSONResponse(
                status_code=403,
                content={"detail": "Invalid API key"}
            )

        return await call_next(request)


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("Starting ClaraVector...")

    # Initialize database
    db = get_database()
    await db.init()
    logger.info("Database initialized")

    # Start embedding queue processor
    queue_processor = get_embedding_queue()
    await queue_processor.start()
    logger.info("Embedding queue processor started")

    yield

    # Shutdown
    logger.info("Shutting down ClaraVector...")
    await queue_processor.stop()
    logger.info("Embedding queue processor stopped")


# Create FastAPI app
app = FastAPI(
    title="ClaraVector",
    description="Lightweight vector-backed document management for Raspberry Pi",
    version="1.0.0",
    lifespan=lifespan
)

# Add middlewares (order matters - first added = last executed)
settings = get_settings()

# API Key authentication
app.add_middleware(APIKeyMiddleware)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=settings.cors_methods_list,
    allow_headers=settings.cors_headers_list,
)

# Include routers
app.include_router(health.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")
app.include_router(notebooks.router, prefix="/api/v1")
app.include_router(documents.router, prefix="/api/v1")
app.include_router(search.router, prefix="/api/v1")
app.include_router(queue.router, prefix="/api/v1")


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "ClaraVector",
        "version": "1.0.0",
        "docs": "/docs"
    }


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        workers=settings.workers,
        reload=False
    )
