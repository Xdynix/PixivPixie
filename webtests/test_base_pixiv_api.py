"""Web tests for pixivpy3.api.BasePixivAPI."""

import pytest
from jsonschema import validate
from pixivpy3.api import BasePixivAPI, PixivError as PixivPyError

from .schemas import AUTH_RESPONSE_SCHEMA
from .secret import SECRET


@pytest.mark.webtest
def test_auth():
    """Test authenticate with username+password and refresh token."""

    api = BasePixivAPI(**SECRET['requests_kwargs'])

    response = api.auth(username=SECRET['username'], password=SECRET['password'])
    validate(instance=response, schema=AUTH_RESPONSE_SCHEMA)

    refresh_token = response.response.refresh_token
    response = api.auth(refresh_token=refresh_token)
    validate(instance=response, schema=AUTH_RESPONSE_SCHEMA)


@pytest.mark.webtest
def test_auth_failed():
    """Test BasePixivAPI behavior on failed authentication."""

    api = BasePixivAPI(**SECRET['requests_kwargs'])

    with pytest.raises(PixivPyError):
        api.auth(username='bad-user@example.com', password='password')

    with pytest.raises(PixivPyError):
        api.auth(refresh_token='1234567890')
