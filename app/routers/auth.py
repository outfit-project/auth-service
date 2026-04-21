from fastapi import APIRouter, Depends, HTTPException, status

from app.core.security.deps import get_current_user
from app.routers.deps import (
    get_login_service,
    get_refresh_service,
    get_register_service,
    get_verify_service,
)
from app.schemas.user import (
    MessageSchema,
    RefreshTokenSchema,
    ResendCodeSchema,
    TokenSchema,
    UserLoginSchema,
    UserPayload,
    UserRegisterSchema,
    VerifyCodeSchema,
)
from app.services.errors import (
    InvalidCredentialsError,
    InvalidRefreshTokenError,
    InvalidVerificationCodeError,
    RateLimitedError,
    UserAlreadyExistsError,
)
from app.services.login_service import LoginService
from app.services.refresh_service import RefreshService
from app.services.register_service import RegisterService
from app.services.verify_service import VerifyService

router = APIRouter()


@router.post(
    "/register",
    response_model=MessageSchema,
    status_code=status.HTTP_202_ACCEPTED,
)
async def register(
    payload: UserRegisterSchema,
    service: RegisterService = Depends(get_register_service),
) -> MessageSchema:
    try:
        await service.start_registration(
            email=payload.email,
            username=payload.username,
            password=payload.password,
        )
    except UserAlreadyExistsError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc))
    except RateLimitedError as exc:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, str(exc))
    return MessageSchema(message="Verification code sent")


@router.post("/verify", response_model=TokenSchema)
async def verify(
    payload: VerifyCodeSchema,
    service: VerifyService = Depends(get_verify_service),
) -> TokenSchema:
    try:
        tokens = await service.verify(email=payload.email, code=payload.code)
    except InvalidVerificationCodeError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))
    except UserAlreadyExistsError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc))
    return TokenSchema(**tokens)


@router.post("/resend-code", response_model=MessageSchema)
async def resend_code(
    payload: ResendCodeSchema,
    service: RegisterService = Depends(get_register_service),
) -> MessageSchema:
    try:
        await service.resend_code(payload.email)
    except RateLimitedError as exc:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, str(exc))
    return MessageSchema(message="If a pending registration exists, a new code has been sent")


@router.post("/login", response_model=TokenSchema)
async def login(
    payload: UserLoginSchema,
    service: LoginService = Depends(get_login_service),
) -> TokenSchema:
    try:
        tokens = await service.login(
            username=payload.username,
            password=payload.password,
        )
    except InvalidCredentialsError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(exc))
    return TokenSchema(**tokens)


@router.post("/refresh", response_model=TokenSchema)
async def refresh(
    payload: RefreshTokenSchema,
    service: RefreshService = Depends(get_refresh_service),
) -> TokenSchema:
    try:
        tokens = await service.refresh(payload.refresh_token)
    except InvalidRefreshTokenError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(exc))
    return TokenSchema(**tokens)


@router.get("/me", response_model=UserPayload)
async def me(current_user: UserPayload = Depends(get_current_user)) -> UserPayload:
    return current_user
