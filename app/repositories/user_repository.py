import uuid

from sqlalchemy import select

from app.db.session import SessionDep
from app.models.user import User
from app.schemas.user import UserSchema


class UserRepository:
    def __init__(self, session: SessionDep):
        self._session = session

    async def add(self, user: UserSchema) -> User:
        new_user = User(
            username=user.username,
            password=user.password_hash,
            is_active=user.is_active,
            is_staff=user.is_staff,
        )

        self._session.add(new_user)

        await self._session.commit()
        await self._session.refresh(new_user)

        return new_user

    async def get_user_by_id(self, user_id: uuid.UUID) -> UserSchema:
        query = select(User).where(User.id == user_id)
        result = await self._session.execute(query)

        user = await result.scalars().all()

        return user

    async def get_by_username(self, username: str) -> User | None:
        result = await self._session.execute(select(User).where(User.username == username))
        row = result.scalar_one_or_none()
        return row
