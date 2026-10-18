from types import SimpleNamespace
from uuid import uuid4

import fakeredis.aioredis
import pytest
from pydantic import ValidationError

from app.schemas.user import UserRegisterSchema

from app.core.security.password import PasswordHasher
from app.core.security.tokens import JWTTokenProvider
from app.repositories.pending_registration import PendingRegistrationRepository
from app.services.errors import InvalidVerificationCodeError, RateLimitedError, InvalidRefreshTokenError
from app.services.login_service import LoginService
from app.services.mail_service import MailService
from app.services.refresh_service import RefreshService
from app.services.register_service import RegisterService
from app.services.verify_service import VerifyService


class Users:
    def __init__(self):
        self.users = []

    async def exists_by_email_or_username(self, email, username):
        return any(u.email == email.lower() or u.username == username for u in self.users)

    async def add(self, **values):
        user = SimpleNamespace(id=uuid4(), is_active=True, is_staff=False, **values)
        self.users.append(user)
        return user

    async def get_by_id(self, user_id):
        return next((u for u in self.users if u.id == user_id), None)

    async def get_by_username(self, username):
        return next((u for u in self.users if u.username == username), None)


def test_registration_rejects_email_localparts_that_require_smtputf8():
    with pytest.raises(ValidationError):
        UserRegisterSchema(email="пользователь@example.com", username="person", password="Example-password-1")


def test_registration_accepts_international_email_domains():
    payload = UserRegisterSchema(email="person@пример.рф", username="person", password="Example-password-1")
    assert str(payload.email) == "person@пример.рф"


@pytest.mark.asyncio
async def test_registration_mail_verification_login_and_refresh():
    redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    try:
        users, hasher, tokens = Users(), PasswordHasher(), JWTTokenProvider()
        pending = PendingRegistrationRepository(redis)
        register = RegisterService(users, pending, hasher, MailService(redis))
        await register.start_registration(email="person@example.com", username="person", password="Example-password-1")
        assert users.users == []
        messages = await redis.xrange("mail:outbox")
        assert len(messages) == 1
        event = messages[0][1]
        assert event["email"] == "person@example.com"
        assert event["type"] == "verify_code"
        assert len(event["code"]) == 6
        verified = await VerifyService(users, pending, tokens).verify(email=event["email"], code=event["code"])
        assert tokens.decode(verified["access_token"], "access")["username"] == "person"
        with pytest.raises(InvalidVerificationCodeError):
            await VerifyService(users, pending, tokens).verify(email=event["email"], code=event["code"])
        login = await LoginService(users, hasher, tokens).login(username="person", password="Example-password-1")
        refreshed = await RefreshService(users, tokens).refresh(login["refresh_token"])
        assert tokens.decode(refreshed["access_token"], "access")["user_id"] == str(users.users[0].id)
        with pytest.raises(InvalidRefreshTokenError):
            await RefreshService(users, tokens).refresh(login["access_token"])
    finally:
        await redis.aclose()


def test_access_tokens_use_minutes_and_refresh_tokens_cannot_authenticate():
    tokens = JWTTokenProvider(access_expire_min=15)
    access = tokens.create_access_token({"user_id": str(uuid4()), "username": "person"})
    payload = tokens.decode(access, "access")
    assert payload["exp"] - payload["iat"] == 900
    refresh = tokens.create_refresh_token(uuid4())
    assert tokens.decode(refresh, "access") is None


@pytest.mark.asyncio
async def test_resend_cooldown_and_wrong_code_limit():
    redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    try:
        pending = PendingRegistrationRepository(redis)
        register = RegisterService(Users(), pending, PasswordHasher(), MailService(redis))
        await register.start_registration(email="person@example.com", username="person", password="Example-password-1")
        with pytest.raises(RateLimitedError):
            await register.resend_code("person@example.com")
        messages = await redis.xrange("mail:outbox")
        code = messages[0][1]["code"]
        wrong = "999999" if code != "999999" else "111111"
        for _ in range(5):
            assert await pending.check_code("person@example.com", wrong) is None
        assert await pending.check_code("person@example.com", code) is None
    finally:
        await redis.aclose()
