import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.core.security.tokens import JWTTokenProvider
from app.schemas.user import UserPayload

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

_token_provider = JWTTokenProvider()


def get_token_provider() -> JWTTokenProvider:
    return _token_provider


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    tokens: JWTTokenProvider = Depends(get_token_provider),
) -> UserPayload:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = tokens.decode(token, expected_type="access")
    if not payload:
        raise credentials_exception

    user_id = payload.get("user_id")
    username = payload.get("username")
    if user_id is None or username is None:
        raise credentials_exception

    try:
        return UserPayload(
            user_id=uuid.UUID(str(user_id)),
            username=username,
            email=payload.get("email", ""),
        )
    except (ValueError, TypeError):
        raise credentials_exception
