import uuid

from pydantic import BaseModel


class UserSchema(BaseModel):
    id:uuid.UUID | None
    username: str
    password_hash: str
    is_active: bool = True
    is_staff: bool = False
