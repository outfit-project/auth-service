from app.repositories.pending_registration import PendingRegistrationRepository
from app.services.abstractions import IPasswordHasher, IUserRepository
from app.services.errors import (
    RateLimitedError,
    UserAlreadyExistsError,
)
from app.services.mail_service import MailService


class RegisterService:
    def __init__(
        self,
        users: IUserRepository,
        pending: PendingRegistrationRepository,
        hasher: IPasswordHasher,
        mail: MailService,
    ) -> None:
        self._users = users
        self._pending = pending
        self._hasher = hasher
        self._mail = mail

    async def start_registration(
        self,
        *,
        email: str,
        username: str,
        password: str,
    ) -> None:
        if not await self._pending.try_lock_resend(email):
            raise RateLimitedError("Try again in a minute")

        if await self._users.exists_by_email_or_username(email, username):
            raise UserAlreadyExistsError("Email or username already in use")

        password_hash = self._hasher.hash(password)
        code = await self._pending.save(
            email=email,
            username=username,
            password_hash=password_hash,
        )
        await self._mail.send_verification_code(email, code)

    async def resend_code(self, email: str) -> None:
        if not await self._pending.try_lock_resend(email):
            raise RateLimitedError("Try again in a minute")

        pending = await self._pending.get(email)
        if pending is None:
            return

        new_code = await self._pending.save(
            email=pending.email,
            username=pending.username,
            password_hash=pending.password_hash,
        )
        await self._mail.send_verification_code(email, new_code)
