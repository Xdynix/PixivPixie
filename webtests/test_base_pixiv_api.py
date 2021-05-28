"""Web tests for pixivpy3.api.BasePixivAPI."""

import pytest
from jsonschema import validate
from pixivpy3.api import BasePixivAPI, PixivError as PixivPyError

from .schemas import AUTH_RESPONSE_SCHEMA
from .secret import SECRET


class TestBasePixivAPI:
    """Web tests for pixivpy3.api.BasePixivAPI."""

    @pytest.fixture
    def api(self):
        """Fixture that returns a BasePixivAPI object."""
        return BasePixivAPI(**SECRET['requests_kwargs'])

    @pytest.mark.skipif(
        'username' not in SECRET or 'password' not in SECRET,
        reason='username and password not provided',
    )
    @pytest.mark.xfail(reason='username and password no longer supported')
    def test_auth_username_and_password(self, api):
        """Test authenticate with username and password."""
        response = api.auth(username=SECRET['username'], password=SECRET['password'])
        validate(instance=response, schema=AUTH_RESPONSE_SCHEMA)

    def test_auth_refresh_token(self, api):
        """Test authenticate with refresh token."""
        response = api.auth(refresh_token=SECRET['refresh_token'])
        validate(instance=response, schema=AUTH_RESPONSE_SCHEMA)

    def test_auth_failed(self, api):
        """Test BasePixivAPI behavior on failed authentication."""
        with pytest.raises(PixivPyError):
            api.auth(username='bad-user@example.com', password='password')
        with pytest.raises(PixivPyError):
            api.auth(refresh_token='1234567890')
