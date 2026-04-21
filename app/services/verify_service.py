from app.repositories.pending_registration import PendingRegistrationRepository
from app.services._payload import build_access_payload
from app.services.abstractions import ITokenProvider, IUserRepository
from app.services.errors import (
    InvalidVerificationCodeError,
    UserAlreadyExistsError,
)


class VerifyService:
    def __init__(
        self,
        users: IUserRepository,
        pending: PendingRegistrationRepository,
        tokens: ITokenProvider,
    ) -> None:
        self._users = users
        self._pending = pending
        self._tokens = tokens

    async def verify(self, *, email: str, code: str) -> dict:
        data = await self._pending.check_code(email, code)
        if data is None:
            raise InvalidVerificationCodeError("Invalid or expired code")

        if await self._users.exists_by_email_or_username(data.email, data.username):
            await self._pending.delete(email)
            raise UserAlreadyExistsError("Email or username already in use")

        user = await self._users.add(
            email=data.email,
            username=data.username,
            password_hash=data.password_hash,
        )
        await self._pending.delete(email)

        access = self._tokens.create_access_token(build_access_payload(user))
        refresh = self._tokens.create_refresh_token(user.id)
        return {
            "access_token": access,
            "refresh_token": refresh,
            "token_type": "bearer",
        }
