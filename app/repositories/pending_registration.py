import hashlib
import hmac
import json
import secrets
from dataclasses import asdict, dataclass

from redis.asyncio import Redis

from app.core.config import settings


def _hash_code(code: str) -> str:
    return hmac.new(
        settings.CODE_PEPPER.encode("utf-8"),
        code.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def _generate_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


@dataclass(slots=True)
class PendingRegistration:
    email: str
    username: str
    password_hash: str
    code_hash: str
    attempts: int = 0


class PendingRegistrationRepository:
    """
    Draft registrations stored in Redis until email is verified.

    Keys:
      pending:reg:{email}       -> JSON payload, TTL = PENDING_REG_TTL_SEC
      rate:reg:resend:{email}   -> set with TTL = REG_RESEND_COOLDOWN_SEC
    """

    def __init__(self, redis: Redis) -> None:
        self._r = redis

    @staticmethod
    def _pending_key(email: str) -> str:
        return f"pending:reg:{email.lower()}"

    @staticmethod
    def _resend_key(email: str) -> str:
        return f"rate:reg:resend:{email.lower()}"

    async def try_lock_resend(self, email: str) -> bool:
        """Returns True if the caller is allowed to send a code now."""
        acquired = await self._r.set(
            self._resend_key(email),
            "1",
            ex=settings.REG_RESEND_COOLDOWN_SEC,
            nx=True,
        )
        return bool(acquired)

    async def save(
        self,
        *,
        email: str,
        username: str,
        password_hash: str,
    ) -> str:
        code = _generate_code()
        payload = PendingRegistration(
            email=email.lower(),
            username=username,
            password_hash=password_hash,
            code_hash=_hash_code(code),
            attempts=0,
        )
        await self._r.set(
            self._pending_key(email),
            json.dumps(asdict(payload)),
            ex=settings.PENDING_REG_TTL_SEC,
        )
        return code

    async def get(self, email: str) -> PendingRegistration | None:
        raw = await self._r.get(self._pending_key(email))
        if not raw:
            return None
        data = json.loads(raw)
        return PendingRegistration(**data)

    async def check_code(self, email: str, code: str) -> PendingRegistration | None:
        """
        Validate the verification code WITHOUT consuming the pending record.
        The caller (VerifyService) is responsible for calling `delete(email)`
        only after the user has been successfully written to Postgres,
        otherwise a DB failure would leave the user unable to re-verify.

        Returns the payload on success; None on miss / wrong code / too many attempts.
        On wrong code, increments attempts and deletes the record once the
        limit is reached.
        """
        key = self._pending_key(email)
        raw = await self._r.get(key)
        if not raw:
            return None

        data = json.loads(raw)
        attempts = int(data.get("attempts", 0))

        if attempts >= settings.VERIFY_MAX_ATTEMPTS:
            await self._r.delete(key)
            return None

        if not hmac.compare_digest(data["code_hash"], _hash_code(code)):
            data["attempts"] = attempts + 1
            ttl = await self._r.ttl(key)
            ttl = ttl if ttl and ttl > 0 else settings.PENDING_REG_TTL_SEC
            if data["attempts"] >= settings.VERIFY_MAX_ATTEMPTS:
                await self._r.delete(key)
            else:
                await self._r.set(key, json.dumps(data), ex=ttl)
            return None

        return PendingRegistration(**data)

    async def delete(self, email: str) -> None:
        await self._r.delete(self._pending_key(email))
