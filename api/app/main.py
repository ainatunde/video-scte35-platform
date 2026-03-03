import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .database import engine, Base
from .routers import channels, websocket
from .services.redis_service import close_redis

logging.basicConfig(level=settings.log_level)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up: creating database tables")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    logger.info("Shutting down: closing connections")
    await close_redis()
    await engine.dispose()


app = FastAPI(
    title="SCTE-35 Platform API",
    description="AI-powered SCTE-35 marker insertion for video streaming",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(channels.router, prefix="/api/v1")
app.include_router(websocket.router)


@app.get("/health", tags=["health"])
async def health():
    return {"status": "ok", "version": "0.1.0"}
