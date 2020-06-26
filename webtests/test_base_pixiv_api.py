"""Web tests for pixivpy3.api.BasePixivAPI."""

import pytest
from jsonschema import validate
from pixivpy3.api import BasePixivAPI, PixivError as PixivPyError

from .schemas import AUTH_RESPONSE_SCHEMA
from .secret import SECRET


@pytest.fixture
def api():
    return BasePixivAPI(**SECRET['requests_kwargs'])


def test_auth(api):
    """Test authenticate with username+password and refresh token."""

    response = api.auth(username=SECRET['username'], password=SECRET['password'])
    validate(instance=response, schema=AUTH_RESPONSE_SCHEMA)

    response = api.auth(refresh_token=response['response']['refresh_token'])
    validate(instance=response, schema=AUTH_RESPONSE_SCHEMA)


def test_auth_failed(api):
    """Test BasePixivAPI behavior on failed authentication."""

    with pytest.raises(PixivPyError):
        api.auth(username='bad-user@example.com', password='password')

    with pytest.raises(PixivPyError):
        api.auth(refresh_token='1234567890')
