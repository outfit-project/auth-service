import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.config import settings
from app.core.cors import setup_cors
from app.db.redis import close_redis
from app.db.session import engine
from app.models import user as _user_model
from app.routers import auth as auth_router
from app.routers import health as health_router

logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(settings.SERVICE_NAME)


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield

    await engine.dispose()
    await close_redis()


app = FastAPI(
    title=settings.SERVICE_NAME,
    lifespan=lifespan,
)

setup_cors(app)

app.include_router(auth_router.router, prefix="/auth", tags=["auth"])
app.include_router(health_router.router, prefix="/health", tags=["health"])


@app.get("/")
async def root() -> dict:
    return {"service": settings.SERVICE_NAME, "status": "ok"}
