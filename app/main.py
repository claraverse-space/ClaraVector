from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.api.dependencies import get_database, get_embedding_queue
from app.api.routes import health, users, notebooks, documents, search, queue


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

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for your needs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
