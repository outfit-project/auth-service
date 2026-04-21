from fastapi import Depends

from app.core.security.password import PasswordHasher
from app.core.security.tokens import JWTTokenProvider
from app.db.redis import RedisDep
from app.db.session import SessionDep
from app.repositories.pending_registration import PendingRegistrationRepository
from app.repositories.user_repository import UserRepository
from app.services.login_service import LoginService
from app.services.mail_service import MailService
from app.services.refresh_service import RefreshService
from app.services.register_service import RegisterService
from app.services.verify_service import VerifyService

_hasher = PasswordHasher()
_tokens = JWTTokenProvider()


def get_password_hasher() -> PasswordHasher:
    return _hasher


def get_token_provider() -> JWTTokenProvider:
    return _tokens


def get_user_repository(session: SessionDep) -> UserRepository:
    return UserRepository(session)


def get_pending_repository(redis: RedisDep) -> PendingRegistrationRepository:
    return PendingRegistrationRepository(redis)


def get_mail_service(redis: RedisDep) -> MailService:
    return MailService(redis)


def get_register_service(
    users: UserRepository = Depends(get_user_repository),
    pending: PendingRegistrationRepository = Depends(get_pending_repository),
    mail: MailService = Depends(get_mail_service),
    hasher: PasswordHasher = Depends(get_password_hasher),
) -> RegisterService:
    return RegisterService(users=users, pending=pending, hasher=hasher, mail=mail)


def get_verify_service(
    users: UserRepository = Depends(get_user_repository),
    pending: PendingRegistrationRepository = Depends(get_pending_repository),
    tokens: JWTTokenProvider = Depends(get_token_provider),
) -> VerifyService:
    return VerifyService(users=users, pending=pending, tokens=tokens)


def get_login_service(
    users: UserRepository = Depends(get_user_repository),
    hasher: PasswordHasher = Depends(get_password_hasher),
    tokens: JWTTokenProvider = Depends(get_token_provider),
) -> LoginService:
    return LoginService(users=users, hasher=hasher, tokens=tokens)


def get_refresh_service(
    users: UserRepository = Depends(get_user_repository),
    tokens: JWTTokenProvider = Depends(get_token_provider),
) -> RefreshService:
    return RefreshService(users=users, tokens=tokens)
