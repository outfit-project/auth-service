import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(
        self,
        *,
        email: str,
        username: str,
        password_hash: str,
        is_staff: bool = False,
    ) -> User:
        user = User(
            email=email.lower(),
            username=username,
            password_hash=password_hash,
            is_staff=is_staff,
            is_active=True,
        )
        self._session.add(user)
        await self._session.commit()
        await self._session.refresh(user)
        return user

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        result = await self._session.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_by_username(self, username: str) -> User | None:
        result = await self._session.execute(
            select(User).where(User.username == username)
        )
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        result = await self._session.execute(
            select(User).where(User.email == email.lower())
        )
        return result.scalar_one_or_none()

    async def exists_by_email_or_username(self, email: str, username: str) -> bool:
        result = await self._session.execute(
            select(User.id).where(
                (User.email == email.lower()) | (User.username == username)
            )
        )
        return result.first() is not None
