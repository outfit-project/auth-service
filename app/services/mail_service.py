from redis.asyncio import Redis

from app.core.config import settings


class MailService:
    def __init__(self, redis: Redis) -> None:
        self._r = redis

    async def send_verification_code(self, email: str, code: str) -> str:
        return await self._r.xadd(
            settings.MAIL_STREAM,
            {
                "type": "verify_code",
                "email": email,
                "code": code,
            },
            maxlen=100_000,
            approximate=True,
        )
