import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import get_settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("ai_service")

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Lifespan event handler for startup and shutdown procedures."""
    logger.info("Starting AI Knowledge Hub - AI Core Service...")
    logger.info(f"Environment: {settings.ENVIRONMENT} | Port: {settings.PORT}")
    logger.info(f"Embedding Model: {settings.EMBEDDING_MODEL} (dim: {settings.EMBEDDING_DIMENSION})")

    yield

    logger.info("Shutting down AI Core Service cleanly...")


# Initialize FastAPI application
app = FastAPI(
    title="AI Knowledge Hub - AI Core Service",
    description="Python FastAPI service handling Text Extraction, Semantic Chunking, Embeddings, and RAG Pipeline.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get(
    "/",
    status_code=status.HTTP_200_OK,
    tags=["Root"],
    summary="Root welcome endpoint",
)
async def root() -> dict[str, str]:
    """Root endpoint welcoming clients."""
    return {
        "service": "AI Knowledge Hub - AI Core",
        "status": "online",
        "docs": "/docs",
    }


@app.get(
    "/health",
    status_code=status.HTTP_200_OK,
    tags=["Health"],
    summary="Health check endpoint",
)
async def health_check() -> dict[str, str]:
    """Health check endpoint to verify service availability."""
    return {
        "status": "ok",
        "app": "AI Knowledge Hub - AI Core Service",
        "environment": settings.ENVIRONMENT,
    }

