import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from redis.asyncio import Redis
from redis.exceptions import ResponseError

from app.core.config import settings
from app.db.redis import close_redis, get_redis_pool
from app.db.session import engine
from app.models import user as _user_model
from app.routers import auth as auth_router
from app.routers import health as health_router

logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(settings.SERVICE_NAME)


async def _ensure_mail_stream_group() -> None:
    client = Redis(connection_pool=get_redis_pool())
    try:
        try:
            await client.xgroup_create(
                name=settings.MAIL_STREAM,
                groupname=settings.MAIL_GROUP,
                id="$",
                mkstream=True,
            )
            logger.info(
                "Created consumer group %s on %s",
                settings.MAIL_GROUP,
                settings.MAIL_STREAM,
            )
        except ResponseError as exc:
            if "BUSYGROUP" in str(exc):
                logger.debug("Mail consumer group already exists")
            else:
                raise
    finally:
        await client.aclose()


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await _ensure_mail_stream_group()
    except Exception as exc:
        logger.warning("Could not ensure mail stream group: %s", exc)

    yield

    await engine.dispose()
    await close_redis()


app = FastAPI(
    title=settings.SERVICE_NAME,
    lifespan=lifespan,
)

app.include_router(auth_router.router, prefix="/auth", tags=["auth"])
app.include_router(health_router.router, prefix="/health", tags=["health"])


@app.get("/")
async def root() -> dict:
    return {"service": settings.SERVICE_NAME, "status": "ok"}
