"""Exception classes."""


class Error(Exception):
    """Base exception class."""


class AuthError(Error):
    """Errors that occurred during authentication."""


__all__ = (
    'Error',
    'AuthError',
)
