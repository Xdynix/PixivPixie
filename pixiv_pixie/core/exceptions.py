"""Exception classes."""


class Error(Exception):
    """Base exception class."""


class AuthError(Error):
    """Errors that occurred during authentication."""


class LoginFailed(AuthError):
    """Errors that occurred when logging in."""


class RefreshTokenFailed(AuthError):
    """Errors that occurred when trying to refresh access token."""


__all__ = (
    'Error',
    'AuthError',
    'LoginFailed',
    'RefreshTokenFailed',
)
