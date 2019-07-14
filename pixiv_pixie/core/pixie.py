"""The Pixiv API interface."""

from datetime import datetime, timedelta

import attr
from pixivpy3 import PixivAPI, AppPixivAPI
from pixivpy3 import PixivError as PixivPyError
from pixivpy3.api import BasePixivAPI

# pylint: disable=relative-beyond-top-level
from .exceptions import AuthError
from .types import User


@attr.s
class Session:
    # noinspection PyUnresolvedReferences
    """Authenticated session.

    Attributes:
        access_token (str): The token needed to access Pixiv's resources.
        refresh_token (str): The token needed to obtain a new access token.
        expires_in (int): The maximum age of access token in seconds.
        create_date (datetime): The time when the `Session` object was created.
            Used to determine if the access token has expired.
        user (User, optional): The user who has logged in to the session.
    """
    access_token = attr.ib(default='', type=str)
    refresh_token = attr.ib(default='', type=str)
    expires_in = attr.ib(default=3600, type=int)
    create_date = attr.ib(factory=datetime.utcnow, type=datetime)
    user = attr.ib(default=None, type=User)

    @property
    def expiration_date(self):
        """datetime: The time when the access token expired."""
        return self.create_date + timedelta(seconds=self.expires_in)

    def is_expired(self, delta=600):
        """Returns whether the access token has expired.

        Because the expiration time is only a theoretical value, in order to
        avoid the impact of the error, it is considered expired for a short
        period of time before the expiration time.

        Args:
            delta (int): The length of expiration decision interval in seconds.

        Returns:
            `True` if expired. `False` otherwise.
        """
        safe_expiration_date = self.expiration_date - timedelta(seconds=delta)
        return datetime.utcnow() >= safe_expiration_date


class PixivPixie:
    def __init__(self, **requests_kwargs):
        self._requests_kwargs = requests_kwargs
        self._session = None
        self._papi = PixivAPI(**requests_kwargs)
        self._aapi = AppPixivAPI(**requests_kwargs)

    @property
    def requests_kwargs(self):
        return self._requests_kwargs

    @requests_kwargs.setter
    def requests_kwargs(self, requests_kwargs):
        self._requests_kwargs = requests_kwargs
        self._papi.requests_kwargs = requests_kwargs
        self._aapi.requests_kwargs = requests_kwargs

    @property
    def session(self):
        return self._session

    @session.setter
    def session(self, session):
        self._session = session
        self._papi.set_auth(session.access_token, session.refresh_token)
        self._papi.user_id = session.user.id  # will not use
        self._aapi.set_auth(session.access_token, session.refresh_token)
        self._aapi.user_id = session.user.id  # will not use

    def login(self, username, password):
        try:
            self.session = self._auth(username, password)
        except PixivPyError:
            raise AuthError('Please check your username and password.')

    def refresh_session(self, refresh_token=None):
        if refresh_token is None:
            if self.session is None:
                raise AuthError('Please provide a refresh token.')
            refresh_token = self.session.refresh_token
        try:
            self.session = self._auth(refresh_token=refresh_token)
        except PixivPyError:
            raise AuthError('Invalid refresh token.')

    def _auth(self, username=None, password=None, refresh_token=None):
        """Call PixivPy's `auth()` and parse response to `Session` object. Will
        not affect current state even when failed.

        When a username and password are provided, `_auth()` will try to use
        them to authenticate. Otherwise `_auth()` will try to use refresh token
        to authenticate.

        Args:
            username (str): The account name used when the user logs in.
            password (str): The password.
            refresh_token (str): The refresh token obtained before.

        Returns:
            Session: The authenticated session.

        Raises:
            pixivpy3.PixivError: If authentication failed.
        """
        api = BasePixivAPI(**self.requests_kwargs)
        response = api.auth(username, password, refresh_token).response
        # TODO: Check response schema in compatibility test.
        return Session(
            access_token=response.access_token,
            refresh_token=response.refresh_token,
            expires_in=response.expires_in,
            user=User(
                id=response.user.id,
                account=response.user.account,
                name=response.user.name,
                profile_image_url=response.user.profile_image_urls.px_170x170,
            ),
        )


__all__ = (
    'Session',
    'PixivPixie',
)
