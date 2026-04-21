from app.services._payload import build_access_payload
from app.services.abstractions import (
    IPasswordHasher,
    ITokenProvider,
    IUserRepository,
)
from app.services.errors import InvalidCredentialsError


class LoginService:
    def __init__(
        self,
        users: IUserRepository,
        hasher: IPasswordHasher,
        tokens: ITokenProvider,
    ) -> None:
        self._users = users
        self._hasher = hasher
        self._tokens = tokens

    async def login(self, *, username: str, password: str) -> dict:
        user = await self._users.get_by_username(username)
        if not user or not self._hasher.verify(password, user.password_hash):
            raise InvalidCredentialsError("Invalid username or password")
        if not user.is_active:
            raise InvalidCredentialsError("User is inactive")

        access = self._tokens.create_access_token(build_access_payload(user))
        refresh = self._tokens.create_refresh_token(user.id)
        return {
            "access_token": access,
            "refresh_token": refresh,
            "token_type": "bearer",
        }
