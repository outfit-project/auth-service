from fastapi import APIRouter, HTTPException, status
from sqlalchemy import text

from app.db.redis import RedisDep
from app.db.session import SessionDep

router = APIRouter()


@router.get("/live")
async def live() -> dict:
    return {"status": "ok"}


@router.get("/ready")
async def ready(session: SessionDep, redis: RedisDep) -> dict:
    try:
        await session.execute(text("SELECT 1"))
    except Exception as exc:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"postgres unavailable: {exc!s}",
        )
    try:
        pong = await redis.ping()
        if not pong:
            raise RuntimeError("redis ping returned falsy value")
    except Exception as exc:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"redis unavailable: {exc!s}",
        )
    return {"status": "ready"}
