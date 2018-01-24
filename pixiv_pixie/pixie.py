import datetime
import io
import os
import re
from threading import Lock
from zipfile import ZipFile

import dateutil.parser
import imageio
import requests
from pixivpy3 import PixivAPI, AppPixivAPI, PixivError

from .constants import illust as illust_constants
from .constants import ranking as ranking_constants
from .constants import search as search_constants
from .exceptions import LoginFailed, NoAuth, IllustError, APIError
from .illust import PixivIllust
from .utils.datatypes import JsonDict
from .utils.query_set import query_set

TOKEN_LIFETIME = datetime.timedelta(seconds=1800)  # In fact 3600.


class PixivPixie(object):
    """Pixiv API interface.

    Remember call login() before using other methods.

    Attributes:
        auto_re_login: If true, PixivPixie will auto re-login when login token
            expired.
    """

    def __init__(self, auto_re_login=True, **requests_kwargs):
        self.auto_re_login = auto_re_login
        self._requests_kwargs = requests_kwargs

        self._papi = PixivAPI(**requests_kwargs)
        self._aapi = AppPixivAPI(**requests_kwargs)

        self._has_auth = False

        self._username = None
        self._password = None
        self._last_login = None
        self._check_auth_lock = Lock()

    def get_requests_kwargs(self):
        return self._requests_kwargs

    def set_requests_kwargs(self, requests_kwargs):
        self._requests_kwargs = requests_kwargs
        self._papi.requests_kwargs = requests_kwargs
        self._aapi.requests_kwargs = requests_kwargs

    requests_kwargs = property(
        get_requests_kwargs,
        set_requests_kwargs,
        doc="Parameters that will be passed to requests.",
    )

    @property
    def has_auth(self):
        """Whether the pixie has login."""
        return self._has_auth

    @property
    def last_login(self):
        """Last login time. Will be a datetime object or None if haven't login
        yet."""
        return self._last_login

    def login(self, username, password):
        """Login Pixiv account.

        Notice: The access token will expire after about 1 hour. So if you are
            dealing with a long time quest, remember to re-login every some
            time.

        Args:
            username: Your Pixiv account's username.
            password: Your Pixiv account's password.

        Returns:
            None.

        Raises:
            LoginFailed: An error occurred if the username and password is not
                match.
        """
        if not username or not password:
            raise LoginFailed
        try:
            self._papi.login(username, password)
            # self._aapi.login(username, password)
            self._aapi.access_token = self._papi.access_token
            self._aapi.user_id = self._papi.user_id
            self._aapi.refresh_token = self._papi.refresh_token
        except PixivError:
            raise LoginFailed
        else:
            self._has_auth = True
            self._username = username
            self._password = password
            self._last_login = datetime.datetime.now()

    def check_auth(self, auto_re_login=False):
        """Raise error if the pixie doesn't has auth.

        Args:
            auto_re_login: If true, the PixivPixie will try to re-login when
                login token expired.

        Raises:
            NoAuth: If the PixivPixie hasn't login first.
            LoginFailed: If re-login failed.
        """
        with self._check_auth_lock:
            if not self.has_auth:
                raise NoAuth
            if datetime.datetime.now() - self.last_login >= TOKEN_LIFETIME:
                # Token expired
                if auto_re_login:
                    self.login(self._username, self._password)
                else:
                    raise NoAuth

    def illust(self, illust_id):
        """Gets a single illust.

        Args:
            illust_id: An integer.

        Returns:
            A PixivIllust object.

        Raises:
            Any exceptions check_auth() will raise.
            IllustError: If the illust_id is invalid or the illust is blocked by
                the Pixiv account setting.
        """
        self.check_auth(auto_re_login=self.auto_re_login)
        json_result = JsonDict(self._papi.works(illust_id))
        if json_result.status != 'success':
            error_code = json_result.errors.system.get('code')
            error_message = {
                206: 'Target illust not found.',
                229: 'Illust browsing restricted.',
            }
            raise IllustError(illust_id, error_message.get(error_code))
        return PixivIllust.from_papi(json_result.response[0])

    @classmethod
    def _papi_call(cls, call_func,
                   page=1, per_page=30,
                   iter_target=None, extra_yield=None,
                   **kwargs):
        current_page = page
        while current_page:
            json_result = JsonDict(call_func(
                page=current_page, per_page=per_page, **kwargs
            ))

            if json_result.status != 'success':
                raise APIError(call_func, json_result.errors)

            if iter_target is None:
                target = json_result.response
            else:
                target = iter_target(json_result.response)
            for item in target:
                if extra_yield is None:
                    yield item
                else:
                    yield item, extra_yield(json_result.response)

            current_page = json_result.pagination.next

    def _aapi_call(self, call_func, **kwargs):
        req_auth = True

        while True:
            try:
                if int(kwargs['offset']) <= 5000:
                    break
            except (KeyError, ValueError):
                pass
            json_result = JsonDict(call_func(**kwargs, req_auth=req_auth))

            if 'error' in json_result:
                raise APIError(call_func, json_result.error)

            for item in json_result.illusts:
                yield item

            if json_result.next_url is None:
                break
            kwargs = self._aapi.parse_qs(json_result.next_url)

    @classmethod
    def _papi_result_need_metadata(cls, json_result):
        return json_result.page_count > 1 or json_result.type == 'ugoira'

    @query_set
    def my_following_illusts(self, until=None):
        """Fetch new illusts of following users.

        Fetch new illusts of following users.

        Normal user can only have the first 2000 illust while Premium user can
        have the first 5000.

        If you didn't turn off the browsing restriction in account setting, the
        R-18(G) illusts will be excluded.

        Args:
            until: Could be:
                [default] None: No limit.
                A string or datetime object which corresponding to the earliest
                    creation time of illusts.

        Returns:
            A QuerySet that yield PixivIllust object.

        Raises:
            Any exceptions check_auth() will raise.
        """
        self.check_auth(auto_re_login=self.auto_re_login)
        if isinstance(until, str):
            until = dateutil.parser.parse(until)
        for json_result in self._papi_call(self._papi.me_following_works):
            if self._papi_result_need_metadata(json_result):
                # TODO(Xdynix): Use lazy pattern to improve performance.
                illust = self.illust(json_result.id)  # Fetch metadata
            else:
                illust = PixivIllust.from_papi(json_result)
            if until is not None and illust.creation_time < until:
                return
            yield illust

    @query_set
    def user_illusts(self, user_id):
        """Fetch a user's illusts.

        Fetch a user's illusts.
        If you didn't turn off the browsing restriction in account setting, the
        R-18(G) illusts will be excluded.

        Args:
            user_id: An integer.

        Returns:
            A QuerySet that yield PixivIllust object.

        Raises:
            Any exceptions check_auth() will raise.
            PAPIError: If the user_id is invalid.
        """
        self.check_auth(auto_re_login=self.auto_re_login)
        for json_result in self._papi_call(
                self._papi.users_works, author_id=user_id):
            if self._papi_result_need_metadata(json_result):
                # TODO(Xdynix): Use lazy pattern to improve performance.
                yield self.illust(json_result.id)  # Fetch metadata
            else:
                yield PixivIllust.from_papi(json_result)

    @query_set
    def ranking(
            self, mode=ranking_constants.DAY, date=None,
    ):
        """Fetch all ranking illusts.

        Fetch all ranking illusts and returns them from rank high to low.
        If you didn't turn off the browsing restriction in account setting, the
        R-18(G) illusts will be excluded.

        Args:
            mode: Could be:
                [default] DAY
                WEEK
                MONTH
                DAY_MALE
                DAY_FEMALE
                WEEK_ORIGINAL
                WEEK_ROOKIE
                DAY_MANGA
                DAY_R18
                DAY_MALE_R18
                DAY_FEMALE_R18
                WEEK_R18
                WEEK_R18G

                These constants are defined in pixiv_pixie.constants.ranking.
            date: Could be:
                [default] None: Will fetch the latest ranking.
                A date or datetime object.
                A string in the format of '%Y-%m-%d', e.g., '2017-08-01'.

        Returns:
            A QuerySet that yield PixivIllust object.

        Raises:
            Any exceptions check_auth() will raise.
        """
        self.check_auth(auto_re_login=self.auto_re_login)
        if isinstance(date, datetime.date) \
                or isinstance(date, datetime.datetime):
            date = date.strftime('%Y-%m-%d')

        # The response of PAPI does not contains metadata. So AAPI was used.
        for rank, json_result in enumerate(
                self._aapi_call(
                    self._aapi.illust_ranking, mode=mode, date=date),
                start=1
        ):
            if json_result.type == 'ugoira':
                # TODO(Xdynix): Use lazy pattern to improve performance.
                illust = self.illust(json_result.id)  # Fetch metadata
            else:
                illust = PixivIllust.from_aapi(json_result)
            illust.rank = rank
            yield illust

    @query_set
    def search(
            self, query,
            mode=search_constants.TAG,
            period=search_constants.ALL,
            order=search_constants.DESC,
    ):
        """Search illusts.

        Search illusts.

        Args:
            query: Query keyword. You can separate multiple keywords by space.
            mode: Could be:
                TEXT: Search in title and caption.
                [default] TAG: Search in tags.
                EXACT_TAG: Search in tags. Only exactly matched tag is
                    acceptable.
                CAPTION: Search in caption.

                These constants are defined in pixiv_pixie.constants.search.
            period: Could be:
                [default] ALL
                DAY
                WEEK
                MONTH

                This parameter is only applied when order is ASC.
                These constants are defined in pixiv_pixie.constants.search.
            order: Could be:
                [default] DESC: The output will be from new to old.
                ASC: The output will be from old to new.

        Returns:
            A QuerySet that yield PixivIllust object.

        Raises:
            Any exceptions check_auth() will raise.
        """
        self.check_auth(auto_re_login=self.auto_re_login)
        for json_result in self._papi_call(
                self._papi.search_works, query=query,
                mode=mode, period=period, order=order):
            if self._papi_result_need_metadata(json_result):
                # TODO(Xdynix): Use lazy pattern to improve performance.
                yield self.illust(json_result.id)  # Fetch metadata
            else:
                yield PixivIllust.from_papi(json_result)

    @query_set
    def related_illusts(self, illust_id):
        """Fetch all related illusts.

        Fetch all related illusts of a provided illust.

        Args:
            illust_id: An integer.

        Returns:
            A QuerySet that yield PixivIllust object.

        Raises:
            Any exceptions check_auth() will raise.
        """
        self.check_auth(auto_re_login=self.auto_re_login)
        for json_result in self._aapi_call(
                self._aapi.illust_related, illust_id=illust_id):
            if json_result.type == 'ugoira':
                # TODO(Xdynix): Use lazy pattern to improve performance.
                illust = self.illust(json_result.id)  # Fetch metadata
            else:
                illust = PixivIllust.from_aapi(json_result)
            yield illust

    @classmethod
    def convert_zip_to_gif(cls, input_file, frame_delays, output_file=None):
        """Convert a zip file that contains all frames into gif.

        Convert a zip file that contains all frames into gif.

        Args:
            input_file: The input file. May be str or a file-like object.
            frame_delays: A list of delay durations in microsecond.
            output_file: The output file. May be str or a file-like object.
        """
        if output_file is None:
            if isinstance(input_file, str):
                output_file = re.sub(r'\.zip$', '.gif', input_file, flags=re.I)
            else:
                raise ValueError('Could not determined output filename.')
        dir_name = os.path.dirname(output_file)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)

        images = []
        with ZipFile(input_file) as zip_file:
            for name in sorted(zip_file.namelist()):
                with zip_file.open(name) as input_file:
                    images.append(imageio.imread(io.BytesIO(input_file.read())))
        frame_delays = [delay / 1000 for delay in frame_delays]

        # GIF-FI format has better quality, but need addition dll
        imageio.mimwrite(
            output_file, images,
            format='GIF-FI', duration=frame_delays,
        )
        del images

    def _download(self, url, file):
        requests_kwargs = self.requests_kwargs
        requests_kwargs['stream'] = True
        requests_kwargs['headers'] = {
            'Referer': 'https://app-api.pixiv.net/',
        }
        response = requests.get(url, **requests_kwargs)
        try:
            if response.status_code != 200:
                raise APIError('_download', response.text)
            for chunk in response.iter_content(chunk_size=1024):
                if chunk:
                    file.write(chunk)
        finally:
            del response

    def download_illust(
            self, illust, directory=os.path.curdir,
            name=None, addition_naming_info=None,
            convert_ugoira=True, replace=False,
            check_exists=None,
    ):
        """Download illust.

        Download illust.

        Args:
            illust: The illust or illust_id to be downloaded.
            directory: Directory.
            name: If set, the downloaded file would be renamed. Could contains
                format string syntax.
                e.g. name='{illust.user_id}_{original_name}'
                The following information is provided:
                    illust: The illust object.
                    page: 0-based page number.
                    original_name: The default filename.
                    root: The root part of original_name. e.g. 'foo' in
                        'foo.bar'.
                    ext: The extension part of original_name. e.g. '.bar' in
                        'foo.bar'.
            addition_naming_info: Addition dict that will be used when
                formatting name.
            convert_ugoira: Whether to download ugoira as gif. If false, a zip
                file will be downloaded instead. And a txt file contains frame
                durations would be created.
            replace: If true, will replace already exist file(s).
            check_exists: Addition path(s) to check whether the illust exists
                (by name). Could be a path string, a list of path string or
                None.

        Raises:
            Any exceptions check_auth() will raise.
        """
        self.check_auth(auto_re_login=self.auto_re_login)

        if isinstance(illust, int):
            illust = self.illust(illust)

        if check_exists is None:
            check_exists = []
        elif isinstance(check_exists, str):
            check_exists = [check_exists]

        for page, url in enumerate(illust.image_urls):

            original_name = os.path.basename(url)
            if convert_ugoira:
                original_name = re.sub(
                    r'\.zip$', '.gif', original_name, flags=re.IGNORECASE,
                )
            root, ext = os.path.splitext(original_name)

            if name:
                naming_info = dict(
                    illust=illust, page=page,
                    original_name=original_name,
                    root=root, ext=ext,
                )
                if addition_naming_info:
                    naming_info.update(addition_naming_info)
                filename = name.format(**naming_info)
            else:
                filename = original_name

            file_path = os.path.join(directory, filename)
            if not replace and os.path.exists(file_path):
                continue
            if self._check_exist(file_path, check_exists):
                continue

            dir_name = os.path.dirname(file_path)
            if dir_name:
                os.makedirs(dir_name, exist_ok=True)
            buffer = io.BytesIO()
            try:
                self._download(url, buffer)
                buffer.seek(0)

                if illust.type == illust_constants.UGOIRA and convert_ugoira:
                    self.convert_zip_to_gif(
                        buffer, illust.frame_delays, file_path,
                    )
                else:
                    with open(file_path, 'wb') as f:
                        f.write(buffer.read())

                if illust.type == illust_constants.UGOIRA \
                        and not convert_ugoira:
                    with open(os.path.splitext(file_path)[0] + '.txt',
                              'wt') as f:
                        for frame_delay in illust.frame_delays:
                            f.write('{}\n'.format(frame_delay))
            except Exception as e:
                try:
                    os.remove(file_path)
                except OSError:
                    pass
                finally:
                    raise e
            finally:
                del buffer

    download = download_illust  # shorthand

    @classmethod
    def _check_exist(cls, path, checklist):
        basename = os.path.basename(path)
        for folder in checklist:
            if os.path.exists(os.path.join(folder, basename)):
                return True
        return False
