"""Utility functions for unit test."""

import json
from datetime import datetime
from typing import Union

import attr


def get_fake_datetime(now: datetime):
    """Generate monkey patch class for `datetime.datetime`, whose now() and utcnow() always returns given value."""

    class FakeDatetime:
        """Fake datetime.datetime class."""

        @classmethod
        def now(cls):
            """Return given value."""
            return now

        @classmethod
        def utcnow(cls):
            """Return given value."""
            return now

    return FakeDatetime


def get_fake_response_factory(content: Union[str, list, dict], status_code: int = 200):
    """Generate monkey patch function that always returns FakeResponse, which acts like requests.Response."""

    @attr.s(auto_attribs=True)
    class FakeResponse:
        # noinspection PyUnresolvedReferences
        """Fake requests response.

        Attributes:
            text (str): Response content.
            status_code (int): Response status code.
            headers (dict): Response headers.
        """

        text: str
        status_code: int
        headers = {}

    if isinstance(content, str):
        text = content
    elif isinstance(content, (list, dict)):
        text = json.dumps(content)

    def fake_response_factory(*_, **__):
        return FakeResponse(text, status_code)

    return fake_response_factory


__all__ = (
    'get_fake_datetime',
    'get_fake_response_factory',
)
