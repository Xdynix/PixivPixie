"""Main PixivPixie API."""

from datetime import datetime, timedelta
from typing import Dict, Any, Optional

import attr
from pixivpy3 import AppPixivAPI, PixivAPI as PublicPixivAPI, PixivError as PixivPyError

from .base import PixivInterface
from .exceptions import AuthFailed
from .illust import User


@attr.s(auto_attribs=True)
class Session:
    # noinspection PyUnresolvedReferences
    """Authentication session.

    Attributes:
        access_token (str): The token needed to access Pixiv's resources.
        refresh_token (str): The token needed to obtain a new access token.
        expires_in (int): The maximum age of access token in seconds.
        create_date (:obj:`datetime`): The time when the `Session` object was created.
            Used to determine if the access token has expired.
        user (:obj:`User`, optional): The user who has logged in to the session.
    """

    access_token: str = ''
    refresh_token: str = ''
    expires_in: int = 3600
    create_date: datetime = attr.ib(factory=datetime.utcnow)
    user: User = None

    @property
    def expiration_date(self) -> datetime:
        """:obj:`datetime`: The time when the access token expired."""

        return self.create_date + timedelta(seconds=self.expires_in)

    def is_expired(self, approx: int = 300) -> bool:
        """Returns whether the access token has expired.

        Because the expiration time is only a theoretical value, in order to avoid the impact of the error,
        it is considered expired for a short period of time before the expiration time.

        Args:
            approx (int): The length of expiration decision interval in seconds. Default to 300.

        Returns:
            True if expired. False otherwise.

        Raises:
            ValueError: If `approx` is smaller than zero.
        """

        if approx < 0:
            raise ValueError(f'`approx` should be greater or equal to 0, got {approx}')
        return datetime.utcnow() >= self.expiration_date - timedelta(seconds=approx)


class PixivPixie(PixivInterface):
    """PixivPixie API.

    The main API class that will be communicate with Pixiv. In most case, you need to authenticate first.
    There are two ways to authenticate:
        1. Use `PixivPixie.login(username, password)` with your username and password.
            Pixiv may send you an email to notify you of a new login.
        2. After you have authenticated, you can get the refresh token from `PixivPixie.session.refresh_token`.
            You can save it in a file or elsewhere for future authentication.
            The way to use refresh token authentication is `PixivPixie.refresh_session(refresh_token)`.
            You can also use `PixivPixie.refresh_session()` for shorthand to refresh current session.

    Args:
        **requests_kwargs: Keyword arguments that will be passed to `requests`.
    """

    def __init__(self, **requests_kwargs):
        super().__init__()
        self._requests_kwargs: Dict[str, Any] = requests_kwargs
        self._session: Optional[Session] = None
        self._aapi = AppPixivAPI(**requests_kwargs)
        self._papi = PublicPixivAPI(**requests_kwargs)

    def __repr__(self):
        return f'{self.__class__.__name__}(**{self.requests_kwargs!r})'

    @property
    def requests_kwargs(self) -> Dict[str, Any]:
        """dict: Current keyword arguments passed to `requests`."""

        return self._requests_kwargs

    @requests_kwargs.setter
    def requests_kwargs(self, requests_kwargs: Dict[str, Any]):
        self._requests_kwargs = requests_kwargs
        self._aapi.requests_kwargs = requests_kwargs
        self._papi.requests_kwargs = requests_kwargs

    @property
    def session(self) -> Optional[Session]:
        """:obj:`Session`: Current authenticated session, if any, otherwise `None`."""

        return self._session

    @session.setter
    def session(self, session: Session):
        self._session = session
        self._aapi.set_auth(session.access_token, session.refresh_token)
        self._papi.set_auth(session.access_token, session.refresh_token)

    @property
    def user(self) -> Optional[User]:
        """A shorthand for retrieving current session's user."""

        if self.session is None:
            return None
        return self.session.user

    def set_additional_headers(self, headers: Dict[str, str]):
        """Set additional headers, overwrite API default headers in case of collision."""

        self._aapi.set_additional_headers(headers)
        self._papi.set_additional_headers(headers)

    def set_accept_language(self, language: str):
        """Set 'Accept-Language' header. Useful to get `tags.translated_name`."""

        self._aapi.set_accept_language(language)
        self._papi.set_accept_language(language)

    def _auth(self, username: str = None, password: str = None, refresh_token: str = None) -> Session:
        try:
            response = self._aapi.auth(username, password, refresh_token)['response']
        except PixivPyError as ex:
            raise AuthFailed(str(ex))
        else:
            return Session(
                access_token=response['access_token'],
                refresh_token=response['refresh_token'],
                expires_in=response['expires_in'],
                user=User(
                    id=int(response['user']['id']),
                    account=response['user']['account'],
                    name=response['user']['name'],
                    profile_image_url=response['user']['profile_image_urls']['px_170x170'],
                ),
            )

    def login(self, username: str, password: str):
        """Authenticate with username and password.

        Args:
            username (str): The account name used when the user logs in. Usually is the email address or a shorter Pixiv ID.
            password (str): The password.

        Raises:
            AuthFailed: If the username and password is incorrect.
        """

        self.session = self._auth(username=username, password=password)

    def refresh_session(self, refresh_token: str = None):
        """Authenticate with refresh token.

        Args:
            refresh_token (str, optional): The refresh token. If not present, will try to use current session's refresh token.

        Raises:
            ValueError: If neither a refresh token is provided nor an authenticated session exists.
            AuthFailed: If the refresh token is incorrect.
        """

        if refresh_token is None and self.session is None:
            raise ValueError('No available refresh token.')
        self.session = self._auth(refresh_token=refresh_token or self.session.refresh_token)


__all__ = (
    'Session',
    'PixivPixie',
)
