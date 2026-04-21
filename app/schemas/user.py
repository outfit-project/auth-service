import uuid

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserOut(BaseModel):
    id: uuid.UUID
    email: EmailStr
    username: str
    is_active: bool
    is_staff: bool

    model_config = ConfigDict(from_attributes=True)


class UserRegisterSchema(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=128)
    password: str = Field(..., min_length=8, max_length=128)


class UserLoginSchema(BaseModel):
    username: str
    password: str


class VerifyCodeSchema(BaseModel):
    email: EmailStr
    code: str = Field(..., min_length=6, max_length=6, pattern=r"^\d{6}$")


class ResendCodeSchema(BaseModel):
    email: EmailStr


class TokenSchema(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshTokenSchema(BaseModel):
    refresh_token: str


class UserPayload(BaseModel):
    user_id: uuid.UUID
    username: str
    email: str = ""


class MessageSchema(BaseModel):
    message: str
