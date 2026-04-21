from app.models.user import User


def build_access_payload(user: User) -> dict:
    return {
        "user_id": str(user.id),
        "username": user.username,
        "email": user.email,
        "is_staff": user.is_staff,
    }
