# pylint: disable=unused-argument
"""Unit tests for pixiv_pixie.core.pixie."""

from datetime import datetime, timedelta
from unittest.mock import patch

import pytest
from pixivpy3 import AppPixivAPI, PixivAPI as PublicPixivAPI
from pixivpy3.api import BasePixivAPI

import pixiv_pixie.core.pixie
from pixiv_pixie.core.exceptions import AuthFailed
from pixiv_pixie.core.illust import User
from pixiv_pixie.core.pixie import Session, PixivPixie
from ..utils import get_fake_datetime, get_fake_response_factory


class TestSession:
    """Unit tests for Session."""

    def test_create_date_default(self):
        """Test that the default value of Session.create_date is datetime.utcnow()."""

        now = datetime.utcnow()
        session = Session()
        # It's hard to mock the default factory of Session.create_date, therefore only approximate comparisons are made.
        assert now - timedelta(seconds=2) < session.create_date < now + timedelta(seconds=2)

    def test_expiration_date(self):
        """Test the calculation of `expiration_date`."""

        assert Session(create_date=datetime(2000, 1, 1, 0)).expiration_date == datetime(2000, 1, 1, 1)
        assert Session(expires_in=4200, create_date=datetime(2000, 1, 1, 0)).expiration_date == datetime(2000, 1, 1, 1, 10)

    def test_is_expired(self, monkeypatch):
        """Test the calculation of `expiration_date`."""

        now = datetime(2000, 1, 1, 12)
        monkeypatch.setattr(pixiv_pixie.core.pixie, 'datetime', get_fake_datetime(now + timedelta(hours=1)))

        assert Session(expires_in=1800, create_date=now).is_expired()
        assert Session(expires_in=3600, create_date=now).is_expired()
        assert Session(expires_in=7200, create_date=now).is_expired() is False

        assert Session(expires_in=3700, create_date=now).is_expired(approx=0) is False
        assert Session(expires_in=3700, create_date=now).is_expired()
        assert Session(expires_in=3700, create_date=now).is_expired(approx=900)

        with pytest.raises(ValueError):
            Session().is_expired(approx=-1)


class TestPixivPixie:
    """Unit tests for PixivPixie."""

    fake_auth_response = {'response': {
        'access_token': 'access_token',
        'refresh_token': 'refresh_token',
        'expires_in': 1800,
        'user': {
            'id': '0',
            'account': 'account',
            'name': 'name',
            'profile_image_urls': {'px_170x170': 'https://a.com/b.jpg'},
        },
    }}

    @pytest.fixture
    def pixie(self):
        """Fixture that returns a PixivPixie object."""
        return PixivPixie()

    @pytest.fixture
    def mock_auth_response(self, monkeypatch):
        """Mock `BasePixivAPI.requests_call()` so that it always returns success authentication response."""

        monkeypatch.setattr(
            BasePixivAPI,
            'requests_call',
            get_fake_response_factory(self.fake_auth_response),
        )

    @pytest.fixture
    def mock_auth_response_failed(self, monkeypatch):
        """Mock `BasePixivAPI.requests_call()` so that it always returns failed authentication response."""

        monkeypatch.setattr(
            BasePixivAPI,
            'requests_call',
            get_fake_response_factory('', status_code=403),
        )

    def test_requests_kwargs(self, pixie):
        """Test the get and set of `requests_kwargs`."""

        assert not pixie.requests_kwargs
        requests_kwargs = {'proxies': {
            'http': 'http://127.0.0.1:1080',
            'https': 'http://127.0.0.1:1080',
        }}
        pixie.requests_kwargs = requests_kwargs
        assert pixie.requests_kwargs == requests_kwargs

    def test_session(self, pixie):
        """Test the get and set of `session`."""

        assert pixie.session is None
        session = Session(
            access_token='access_token',
            refresh_token='refresh_token',
            create_date=datetime(2000, 1, 1),
        )
        pixie.session = session
        assert pixie.session == session

    def test_user(self, pixie):
        """Test the get of `user`."""

        assert pixie.user is None
        user = User()
        pixie.session = Session(user=user)
        assert pixie.user == user

    def test_set_additional_headers(self, pixie):
        """Test `set_additional_headers()` behavior."""

        headers = {
            'User-Agent': 'Foobar',
        }
        with patch.object(AppPixivAPI, 'set_additional_headers') as mock_aapi_set_additional_headers, \
                patch.object(PublicPixivAPI, 'set_additional_headers') as mock_papi_set_additional_headers:
            pixie.set_additional_headers(headers)
            mock_aapi_set_additional_headers.assert_called_once_with(headers)
            mock_papi_set_additional_headers.assert_called_once_with(headers)

    def test_set_accept_language(self, pixie):
        """Test `set_accept_language()` behavior."""

        accept_language = 'en-US'
        with patch.object(AppPixivAPI, 'set_accept_language') as mock_aapi_set_accept_language, \
                patch.object(PublicPixivAPI, 'set_accept_language') as mock_papi_set_accept_language:
            pixie.set_accept_language(accept_language)
            mock_aapi_set_accept_language.assert_called_once_with(accept_language)
            mock_papi_set_accept_language.assert_called_once_with(accept_language)

    def test_login(self, pixie, mock_auth_response):
        """Test `login()` behavior."""

        assert pixie.session is pixie.user is None
        pixie.login('username', 'password')
        assert pixie.session.access_token == 'access_token'
        assert pixie.session.refresh_token == 'refresh_token'
        assert pixie.session.expires_in == 1800
        assert pixie.user == User(id=0, account='account', name='name', profile_image_url='https://a.com/b.jpg')

    def test_refresh_session(self, pixie, mock_auth_response):
        """Test `refresh_session()` behavior."""

        assert pixie.session is pixie.user is None
        pixie.refresh_session('refresh_token')
        assert pixie.session.access_token == 'access_token'
        assert pixie.session.refresh_token == 'refresh_token'
        assert pixie.session.expires_in == 1800
        assert pixie.user == User(id=0, account='account', name='name', profile_image_url='https://a.com/b.jpg')

    def test_refresh_session_without_argument(self, pixie):
        """Test `refresh_session()` behavior without argument."""

        with pytest.raises(ValueError):
            pixie.refresh_session()

        pixie.session = Session(refresh_token='refresh_token')
        with patch.object(BasePixivAPI, 'auth', return_value=self.fake_auth_response) as mock_auth:
            pixie.refresh_session()
            mock_auth.assert_called_once_with(
                username=None,
                password=None,
                refresh_token='refresh_token',
            )

    def test_auth_failed(self, pixie, mock_auth_response_failed):
        """Test `login()` and `refresh_session()` failed."""

        with pytest.raises(AuthFailed):
            pixie.login('username', 'password')
        with pytest.raises(AuthFailed):
            pixie.refresh_session('refresh_token')
