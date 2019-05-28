"""Data classes used by pixiv_pixie."""

# pylint: disable=too-few-public-methods

from datetime import datetime
from enum import Enum, unique

import attr

# pylint: disable=relative-beyond-top-level
from ..utils.singleton import Singleton


class _Unknown(metaclass=Singleton):
    """Sentinel class to indicate the lack of a value when `None` is ambiguous.

    `_Unknown` is a singleton. There is only ever one of it.
    """

    def __repr__(self):
        return 'UNKNOWN'


UNKNOWN = _Unknown()


@attr.s
class User:
    # noinspection PyUnresolvedReferences
    """Pixiv user class.

    Data class used to express Pixiv user. Often used for painter information
    and current users.

    Some attributes may have a value of `UNKNOWN`. This is because some APIs
    do not return full information.

    Attributes:
        id (int): User ID.
        account (str): The account name used when the user logs in.
        name (str): Displayed user nickname.
        profile_image_url (str): The URL of the 170x170 version of the user
            avatar.
    """
    id = attr.ib(default=UNKNOWN, type=int)
    account = attr.ib(default=UNKNOWN, type=str)
    name = attr.ib(default=UNKNOWN, type=str)
    profile_image_url = attr.ib(default=UNKNOWN, type=str)
    # TODO: compute small image url (50x50, 16x16)


@attr.s
class Series:
    # noinspection PyUnresolvedReferences
    """Pixiv illustration series class.

    Some attributes may have a value of `UNKNOWN`. This is because some APIs
    do not return full information.

    Attributes:
        id (int): Series ID.
        title (str): Series title.
    """
    id = attr.ib(default=UNKNOWN, type=int)
    title = attr.ib(default=UNKNOWN, type=str)


@unique
class Type(Enum):
    """Describes the illustration type."""

    ILLUST = 'illust'
    MANGA = 'manga'
    UGOIRA = 'ugoira'


@unique
class AgeLimit(Enum):
    """Describes the illustration age limitation."""

    ALL_AGE = 'all-age'
    R18 = 'r18'
    R18G = 'r18-g'


@attr.s
class Illust:
    # noinspection PyUnresolvedReferences
    """Pixiv illustration class.

    Some attributes may have a value of `UNKNOWN`. This is because some APIs
    do not return full information.

    Attributes:
        id (int): Illustration ID.
        user (User): Illustration painter.
        create_date (datetime): The time when the illustration was first
            uploaded.
        title (str): The title of the illustration.
        caption (str): The caption of the illustration.
        series (Series): The series information of the illustration, if any,
            otherwise `None`.
        type (Type): The type of the illustration. Can be one of `ILLUST`,
            `MANGA` and `UGOIRA`.
        age_limit (AgeLimit): The age limitation of the illustration. Can be
            one of `ALL_AGE`, `R18` and `R18G`.
        width (int): The width of the illustration in pixels. If there are
            multiple pages, it only applies to the first page.
        height (int): The height of the illustration in pixels. If there are
            multiple pages, it only applies to the first page.
        page_count (int): The number of pages of the illustration. `ILLUST`
            and `MANGA` can have one or more pages. `UGOIRA` will only have
            one page.
        image_urls (list of str): The URL of the original version of each
            page. This only applies to `ILLUST` and `MANGA`.
        frame_delays (list of int): The duration of each frame in
            milliseconds. This only applies to `UGOIRA`.
        zip_url (str): The URL of the ZIP file containing all frames. This
            only applies to `UGOIRA`.
        tags (list of str): The tags of the illustration.
        tools (list of str): The tools the author used to create the
            illustration.
        total_bookmarks (int): The number of times this illustration was
            bookmarked (both public and non-public).
        total_comments (int): The number of comments under this illustration.
        total_view (int): The number of times this illustration was viewed.
    """
    id = attr.ib(default=UNKNOWN, type=int)
    user = attr.ib(default=UNKNOWN, type=User)
    create_date = attr.ib(default=UNKNOWN, type=datetime)

    title = attr.ib(default=UNKNOWN, type=str)
    caption = attr.ib(default=UNKNOWN, type=str)
    series = attr.ib(default=UNKNOWN, type=Series)

    type = attr.ib(default=UNKNOWN, type=Type)
    # TODO: Reminder: in app api, it's "x_restrict".
    age_limit = attr.ib(default=UNKNOWN, type=AgeLimit)

    width = attr.ib(default=UNKNOWN, type=int)
    height = attr.ib(default=UNKNOWN, type=int)

    page_count = attr.ib(default=UNKNOWN, type=int)
    # TODO: Reminder: in public api, "origin" is "large"
    image_urls = attr.ib(default=UNKNOWN, type=list)
    # TODO: compute small image url
    #  (600x1200_90, 540x540_70, 360x360_70, 128x128, 480x960)
    frame_delays = attr.ib(default=UNKNOWN, type=list)
    zip_url = attr.ib(default=UNKNOWN, type=str)

    tags = attr.ib(default=UNKNOWN, type=list)
    tools = attr.ib(default=UNKNOWN, type=list)

    total_bookmarks = attr.ib(default=UNKNOWN, type=int)
    total_comments = attr.ib(default=UNKNOWN, type=int)
    total_view = attr.ib(default=UNKNOWN, type=int)

    @property
    def shape(self):
        """(int, int): The tuple (width, height)."""
        return self.width, self.height

    @property
    def aspect_ratio(self):
        """float: Width divided by height."""
        if self.height == 0:
            return 0.
        return self.width / self.height


__all__ = (
    'UNKNOWN',
    'User',
    'Series',
    'Type',
    'AgeLimit',
    'Illust',
)
