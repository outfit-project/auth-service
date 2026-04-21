import uuid
from typing import Protocol, runtime_checkable

from app.models.user import User


@runtime_checkable
class IPasswordHasher(Protocol):
    def hash(self, plain: str) -> str: ...
    def verify(self, plain: str, hashed: str) -> bool: ...


@runtime_checkable
class ITokenProvider(Protocol):
    def create_access_token(self, payload: dict) -> str: ...
    def create_refresh_token(self, user_id: uuid.UUID) -> str: ...
    def decode(self, token: str, expected_type: str | None = None) -> dict | None: ...


@runtime_checkable
class IUserRepository(Protocol):
    async def add(
        self,
        *,
        email: str,
        username: str,
        password_hash: str,
        is_staff: bool = False,
    ) -> User: ...

    async def get_by_id(self, user_id: uuid.UUID) -> User | None: ...
    async def get_by_username(self, username: str) -> User | None: ...
    async def get_by_email(self, email: str) -> User | None: ...
    async def exists_by_email_or_username(self, email: str, username: str) -> bool: ...
