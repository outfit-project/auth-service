class AuthError(Exception):
    pass

class InvalidCredentialsError(AuthError):
    pass


class UserAlreadyExistsError(AuthError):
    pass


class PendingRegistrationNotFoundError(AuthError):
    pass


class InvalidVerificationCodeError(AuthError):
    pass


class RateLimitedError(AuthError):
    pass


class InvalidRefreshTokenError(AuthError):
    pass
