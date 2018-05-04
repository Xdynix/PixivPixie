import datetime
from functools import wraps
import io
from itertools import count
import os
from shutil import copyfileobj
from threading import Lock
from zipfile import ZipFile

import dateutil.parser
import imageio
from pixivpy3 import PixivAPI, AppPixivAPI, PixivError
import requests

from .constants import (
    IllustType, RankingMode,
    SearchMode, SearchPeriod, SearchOrder
)
from .exceptions import (
    LoginFailed, NoAuth, IllustError, APIError, DownloadError
)
from .illust import PixivIllust
from .utils import Json, download
from .utils.query_set import query_set

TOKEN_LIFETIME = datetime.timedelta(seconds=1800)  # In fact 3600.

ILLUST_DOWNLOAD_HEADERS = {
    'Referer': 'https://app-api.pixiv.net/',
}


def _need_auth(func):
    @wraps(func)
    def new_func(self, *args, **kwargs):
        self.check_auth(auto_re_login=self.auto_re_login)
        return func(self, *args, **kwargs)

    return new_func


class PixivPixie:
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
        self._last_login = None
        self._check_auth_lock = Lock()

        self._username = None
        self._password = None

    @property
    def requests_kwargs(self):
        """Parameters that will be passed to requests."""
        return self._requests_kwargs

    @requests_kwargs.setter
    def requests_kwargs(self, requests_kwargs):
        self._requests_kwargs = requests_kwargs
        self._papi.requests_kwargs = requests_kwargs
        self._aapi.requests_kwargs = requests_kwargs

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

        return self

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

    @_need_auth
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
        json_result = Json(self._papi.works(illust_id))
        if json_result.status != 'success':
            error_code = json_result.errors.system.get('code')
            error_message = {
                206: 'Target illust not found.',
                229: 'Illust browsing restricted.',
            }
            raise IllustError(illust_id, error_message.get(error_code))
        return PixivIllust.from_papi(self, json_result.response[0])

    @classmethod
    def _papi_call(
            cls, call_func,
            page=1, per_page=30,
            iter_target=None, extra_yield=None,
            **kwargs
    ):
        current_page = page
        while current_page:
            json_result = Json(call_func(
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
                if int(kwargs['offset']) >= 5000:
                    break
            except (KeyError, ValueError):
                pass
            json_result = Json(call_func(**kwargs, req_auth=req_auth))

            if 'error' in json_result:
                raise APIError(call_func, json_result.error)

            yield from json_result.illusts

            if json_result.next_url is None:
                break
            kwargs = self._aapi.parse_qs(json_result.next_url)

    @query_set
    @_need_auth
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
        if isinstance(until, str):
            until = dateutil.parser.parse(until)
        for json_result in self._papi_call(self._papi.me_following_works):
            illust = PixivIllust.from_papi(self, json_result)
            if until is not None and illust.creation_time < until:
                return
            yield illust

    @query_set
    @_need_auth
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
        for json_result in self._papi_call(
                self._papi.users_works, author_id=user_id,
        ):
            yield PixivIllust.from_papi(self, json_result)

    @query_set
    @_need_auth
    def ranking(
            self, mode=RankingMode.DAY, date=None,
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

                These constants are defined in
                    pixiv_pixie.constants.RankingMode.
            date: Could be:
                [default] None: Will fetch the latest ranking.
                A date or datetime object.
                A string in the format of '%Y-%m-%d', e.g., '2017-08-01'.

        Returns:
            A QuerySet that yield PixivIllust object.

        Raises:
            Any exceptions check_auth() will raise.
        """
        if isinstance(date, (datetime.date, datetime.datetime)):
            date = date.strftime('%Y-%m-%d')

        # The response of PAPI does not contains metadata. So AAPI was used.
        for rank, json_result in enumerate(
                self._aapi_call(
                    self._aapi.illust_ranking, mode=mode.value, date=date,
                ),
                start=1
        ):
            illust = PixivIllust.from_aapi(self, json_result)
            illust.rank = rank
            yield illust

    @query_set
    @_need_auth
    def search(
            self, query,
            mode=SearchMode.TAG,
            period=SearchPeriod.ALL,
            order=SearchOrder.DESC,
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

                These constants are defined in pixiv_pixie.constants.SearchMode.
            period: Could be:
                [default] ALL
                DAY
                WEEK
                MONTH

                This parameter is only applied when order is ASC.
                These constants are defined in
                    pixiv_pixie.constants.SearchPeriod.
            order: Could be:
                [default] DESC: The output will be from new to old.
                ASC: The output will be from old to new.

                These constants are defined in
                    pixiv_pixie.constants.SearchOrder.

        Returns:
            A QuerySet that yield PixivIllust object.

        Raises:
            Any exceptions check_auth() will raise.
        """
        for json_result in self._papi_call(
                self._papi.search_works, query=query,
                mode=mode.value, period=period.value, order=order.value,
        ):
            yield PixivIllust.from_papi(self, json_result)

    @query_set
    @_need_auth
    def related_illusts(self, illust_id, limit=None):
        """Fetch all related illusts.

        Fetch all related illusts of a provided illust.

        Args:
            illust_id: An integer.
            limit: Max number of illust to be yield. If limit=None, there will
                be no limit.

        Returns:
            A QuerySet that yield PixivIllust object.

        Raises:
            Any exceptions check_auth() will raise.
        """
        for cnt, json_result in enumerate(self._aapi_call(
                self._aapi.illust_related, illust_id=illust_id,
        ), start=1):
            if limit is not None and cnt > limit:
                break

            yield PixivIllust.from_aapi(self, json_result)

    @classmethod
    def convert_zip_to_gif(
            cls, input_file, frame_delays=None, output_file=None
    ):
        """Convert a zip file that contains all frames into gif.

        Convert a zip file that contains all frames into gif.

        Args:
            input_file: The input file. May be str or a file-like object.
            frame_delays: A list of delay durations in microsecond.
            output_file: The output file. May be str or a file-like object.
        """
        if frame_delays is None:
            if isinstance(input_file, str):
                frame_info = os.path.splitext(input_file)[0] + '.txt'
                with open(frame_info, 'rt', encoding='utf-8') as f:
                    frame_delays = [int(line) for line in f if line.strip()]
            else:
                raise ValueError('Could not get frame delays.')

        if output_file is None:
            if isinstance(input_file, str):
                output_file = os.path.splitext(input_file)[0] + '.gif'
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

    @classmethod
    def _get_file_path(
            cls, illust, page, url,
            convert_ugoira,
            directory, name,
            addition_naming_info,
    ):
        original_name = os.path.basename(url)
        root, ext = os.path.splitext(original_name)

        if convert_ugoira and ext == '.zip':
            ext = '.gif'
            original_name = root + ext

        if name:
            naming_info = {
                'illust': illust,
                'page': page,
                'original_name': original_name,
                'root': root,
                'ext': ext,
            }
            if addition_naming_info:
                naming_info.update(addition_naming_info)
            filename = name.format(**naming_info)
        else:
            filename = original_name

        file_path = os.path.join(directory, filename)

        return file_path

    @classmethod
    def _try_remove_file(cls, path):
        if not isinstance(path, str) or not path:
            return

        try:
            os.remove(path)
        except OSError:
            pass

    @classmethod
    def _check_exist(cls, path, checklist):
        basename = os.path.basename(path)

        for folder in checklist:
            if os.path.exists(os.path.join(folder, basename)):
                return True

        return False

    def _download_illust_to_file(self, url, file):
        requests_kwargs = self.requests_kwargs.copy()
        requests_kwargs['stream'] = True
        requests_kwargs['headers'] = ILLUST_DOWNLOAD_HEADERS

        try:
            wrote_size = 0
            total_size = None

            for wrote_size, total_size in download(
                    file, url, **requests_kwargs,
            ):
                pass

            if total_size is not None and wrote_size < total_size:
                raise APIError(
                    self.download,
                    'Unexpected connection interruption.',
                )

        except requests.HTTPError as e:
            raise APIError(self.download, e.response.text) from e

    def _download_one_url(
            self, illust, url, path,
            convert_ugoira,
            replace,
            check_exists,
            max_tries,
            fake_download,
    ):
        if not replace and os.path.exists(path):
            return False

        if self._check_exist(path, check_exists):
            return False

        if fake_download:
            return False

        dir_name = os.path.dirname(path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)

        frame_path = None

        for tries in count(start=1):
            try:
                buffer = io.BytesIO()
                self._download_illust_to_file(url, buffer)
                buffer.seek(0)

                if illust.type == IllustType.UGOIRA and convert_ugoira:
                    self.convert_zip_to_gif(buffer, illust.frame_delays, path)
                else:
                    with open(path, 'wb') as f:
                        copyfileobj(buffer, f)

                    if illust.type == IllustType.UGOIRA:
                        frame_path = os.path.splitext(path)[0] + '.txt'
                        with open(frame_path, 'wt') as f:
                            for frame_delay in illust.frame_delays:
                                print(frame_delay, file=f)

                return True
            except Exception as e:
                self._try_remove_file(path)
                self._try_remove_file(frame_path)

                if max_tries is None or tries < max_tries:
                    continue

                raise DownloadError(illust, e) from e

    def _download_multiple_urls(
            self, illust, target,
            convert_ugoira,
            replace,
            check_exists,
            max_tries,
            fake_download,
    ):
        result = []

        for url, path in target:
            result.append((url, path, self._download_one_url(
                illust, url, path,
                convert_ugoira=convert_ugoira,
                replace=replace,
                check_exists=check_exists,
                max_tries=max_tries,
                fake_download=fake_download,
            )))

        return result

    @_need_auth
    def download(
            self, illust, directory=os.path.curdir,
            name=None, addition_naming_info=None,
            convert_ugoira=True, replace=False,
            check_exists=None, max_tries=5,
            fake_download=False,
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
            max_tries: Max try times when download failed. If max_tries=None, it
                will loop infinitely until finished.
            fake_download: If True, no file will be actually downloaded.

        Returns:
            A list of download result of each page. Each result is a tuple of
                (url, path, downloaded).

        Raises:
            Any exceptions check_auth() will raise.
            DownloadError.
        """
        if isinstance(illust, int):
            illust = self.illust(illust)

        if check_exists is None:
            check_exists = []
        elif isinstance(check_exists, str):
            check_exists = [check_exists]

        download_target = [
            (
                url,
                self._get_file_path(
                    illust, page, url,
                    convert_ugoira,
                    directory, name,
                    addition_naming_info,
                ),
            )
            for page, url in enumerate(illust.image_urls)
        ]

        return self._download_multiple_urls(
            illust, download_target,
            convert_ugoira=convert_ugoira,
            replace=replace,
            check_exists=check_exists,
            max_tries=max_tries,
            fake_download=fake_download,
        )
