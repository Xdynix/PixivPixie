"""Exceptions."""


class PixieError(Exception):
    """Base exception class."""


class AuthFailed(PixieError):
    """Authentication failed."""


__all__ = (
    'PixieError',
    'AuthFailed',
)
