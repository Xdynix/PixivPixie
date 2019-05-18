"""Simple singleton metaclass."""


class Singleton(type):
    """Singleton metaclass.

    >>> class C(metaclass=Singleton):
    ...     pass
    >>> a = C()
    >>> b = C()
    >>> a is b
    True
    """

    def __init__(cls, *args, **kwargs):
        cls._instance = None
        super().__init__(*args, **kwargs)

    def __call__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__call__(*args, **kwargs)
        return cls._instance


__all__ = (
    'Singleton',
)
