"""Unit tests for pixiv_pixie.core.pixie."""

from datetime import datetime
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

    def test_create_date_default(self, monkeypatch):
        """Test that the default value of Session.create_date is datetime.utcnow()."""

        now = datetime.utcnow()
        monkeypatch.setattr(pixiv_pixie.core.pixie, 'datetime', get_fake_datetime(now))

        assert Session().create_date == now
        assert Session(create_date=datetime(2000, 1, 1)).create_date != now

    def test_expiration_date(self):
        """Test the calculation of `expiration_date`."""

        assert Session(create_date=datetime(2000, 1, 1)).expiration_date == datetime(2000, 1, 1, 1)
        assert Session(expires_in=4200, create_date=datetime(2000, 1, 1)).expiration_date == datetime(2000, 1, 1, 1, 10)

    def test_is_expired(self, monkeypatch):
        """Test the calculation of `expiration_date`."""

        monkeypatch.setattr(pixiv_pixie.core.pixie, 'datetime', get_fake_datetime(datetime(2000, 1, 1, 13)))

        assert Session(expires_in=1800, create_date=datetime(2000, 1, 1, 12)).is_expired()
        assert Session(expires_in=3600, create_date=datetime(2000, 1, 1, 12)).is_expired()
        assert Session(expires_in=7200, create_date=datetime(2000, 1, 1, 12)).is_expired() is False

        assert Session(expires_in=3700, create_date=datetime(2000, 1, 1, 12)).is_expired(approx=0) is False
        assert Session(expires_in=3700, create_date=datetime(2000, 1, 1, 12)).is_expired()
        assert Session(expires_in=3700, create_date=datetime(2000, 1, 1, 12)).is_expired(approx=900)

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

    def test_requests_kwargs(self):
        """Test the get and set of `requests_kwargs`."""

        pixie = PixivPixie()
        assert not pixie.requests_kwargs
        requests_kwargs = {'proxies': {
            'http': 'http://127.0.0.1:1080',
            'https': 'http://127.0.0.1:1080',
        }}
        pixie.requests_kwargs = requests_kwargs
        assert pixie.requests_kwargs == requests_kwargs

    def test_session(self):
        """Test the get and set of `session`."""

        pixie = PixivPixie()
        assert pixie.session is None
        session = Session(
            access_token='access_token',
            refresh_token='refresh_token',
            create_date=datetime(2000, 1, 1),
        )
        pixie.session = session
        assert pixie.session == session

    def test_user(self):
        """Test the get of `user`."""

        pixie = PixivPixie()
        assert pixie.user is None
        user = User()
        pixie.session = Session(user=user)
        assert pixie.user == user

    def test_set_additional_headers(self):
        """Test `set_additional_headers()` behavior."""

        headers = {
            'User-Agent': 'Foobar',
        }

        pixie = PixivPixie()
        with patch.object(AppPixivAPI, 'set_additional_headers'), patch.object(PublicPixivAPI, 'set_additional_headers'):
            pixie.set_additional_headers(headers)
            # noinspection PyUnresolvedReferences
            AppPixivAPI.set_additional_headers.assert_called_once_with(headers)  # pylint: disable=no-member
            # noinspection PyUnresolvedReferences
            PublicPixivAPI.set_additional_headers.assert_called_once_with(headers)  # pylint: disable=no-member

    def test_set_accept_language(self):
        """Test `set_accept_language()` behavior."""

        pixie = PixivPixie()
        with patch.object(AppPixivAPI, 'set_accept_language'), patch.object(PublicPixivAPI, 'set_accept_language'):
            pixie.set_accept_language('en-US')
            # noinspection PyUnresolvedReferences
            AppPixivAPI.set_accept_language.assert_called_once_with('en-US')  # pylint: disable=no-member
            # noinspection PyUnresolvedReferences
            PublicPixivAPI.set_accept_language.assert_called_once_with('en-US')  # pylint: disable=no-member

    @pytest.fixture
    def mock_auth_response(self, monkeypatch):
        """Mock `BasePixivAPI.requests_call()` so that it always returns success authentication response."""

        monkeypatch.setattr(
            BasePixivAPI,
            'requests_call',
            get_fake_response_factory(self.fake_auth_response),
        )

    def test_login(self, mock_auth_response):  # pylint: disable=unused-argument
        """Test `login()` behavior."""

        pixie = PixivPixie()
        assert pixie.session is pixie.user is None
        pixie.login('username', 'password')
        assert pixie.session.access_token == 'access_token'
        assert pixie.session.refresh_token == 'refresh_token'
        assert pixie.session.expires_in == 1800
        assert pixie.user == User(id=0, account='account', name='name', profile_image_url='https://a.com/b.jpg')

    def test_refresh_session(self, mock_auth_response):  # pylint: disable=unused-argument
        """Test `refresh_session()` behavior."""

        pixie = PixivPixie()
        assert pixie.session is pixie.user is None
        pixie.refresh_session('refresh_token')
        assert pixie.session.access_token == 'access_token'
        assert pixie.session.refresh_token == 'refresh_token'
        assert pixie.session.expires_in == 1800
        assert pixie.user == User(id=0, account='account', name='name', profile_image_url='https://a.com/b.jpg')

    def test_refresh_session_without_argument(self):
        """Test `refresh_session()` behavior without argument."""

        pixie = PixivPixie()
        with pytest.raises(ValueError):
            pixie.refresh_session()

        pixie.session = Session(refresh_token='refresh_token')
        with patch.object(BasePixivAPI, 'auth', return_value=self.fake_auth_response):
            pixie.refresh_session()
            # noinspection PyUnresolvedReferences
            BasePixivAPI.auth.assert_called_once_with(None, None, 'refresh_token')  # pylint: disable=no-member

    def test_auth_failed(self, monkeypatch):
        """Test `login()` and `refresh_session()` failed."""

        monkeypatch.setattr(
            BasePixivAPI,
            'requests_call',
            get_fake_response_factory('', status_code=403),
        )

        pixie = PixivPixie()
        with pytest.raises(AuthFailed):
            pixie.login('username', 'password')
        with pytest.raises(AuthFailed):
            pixie.refresh_session('refresh_token')
