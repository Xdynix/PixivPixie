"""Data holders related to illustration."""

from datetime import datetime
from enum import unique, Enum
from typing import List

import attr


@attr.s(auto_attribs=True)
class User:
    # noinspection PyUnresolvedReferences
    """Pixiv user.

    Attributes:
        id (int): User ID.
        account (str): The account name used when the user logs in.
        name (str): The displayed user nickname.
        profile_image_url (str): The URL of the 170×170 version of the user avatar.
    """

    id: int = None
    account: str = None
    name: str = None
    profile_image_url: str = None


@attr.s(auto_attribs=True)
class Series:
    # noinspection PyUnresolvedReferences
    """Manga series.

    Attributes:
        id (int): Series ID.
        title (str): Series title.
    """

    id: int = None
    title: str = None


@unique
class Type(Enum):
    """Illustration type."""

    ILLUST = 'illust'
    MANGA = 'manga'
    UGOIRA = 'ugoira'


@unique
class AgeLimit(Enum):
    """Illustration age limitation."""

    ALL_AGE = 'all-age'
    R18 = 'r18'
    R18G = 'r18-g'


@attr.s(auto_attribs=True)
class Illust:
    # noinspection PyUnresolvedReferences
    """Pixiv illustration.

    Attributes:
        id (int): Illustration ID.
        user (:obj:`User`): Illustration author.
        create_date (:obj:`datetime`): The time when the illustration was first uploaded.
        title (str): The title of the illustration.
        caption (str): The caption of the illustration.
        series (:obj:`Series`): The series information of the illustration, if any, otherwise `None`.
        type (:obj:`Type`): The type of the illustration. Can be one of `ILLUST`, `MANGA` and `UGOIRA`.
        age_limit (:obj:`AgeLimit`): The age limitation of the illustration. Can be one of `ALL_AGE`, `R18` and `R18G`.
        width (int): The width of the illustration in pixels. If there are multiple pages, it only applies to the first page.
        height (int): The height of the illustration in pixels. If there are multiple pages, it only applies to the first page.
        page_count (int): The number of pages of the illustration.
            `ILLUST` and `MANGA` can have one or more pages.
            `UGOIRA` will only have one page.
        image_urls (:obj:`list` of :obj:`str`): The URL of the original version of each page.
            This only applies to `ILLUST` and `MANGA`.
        image_urls_large (:obj:`list` of :obj:`str`): The URL of the large version of each page.
            This only applies to `ILLUST` and `MANGA`.
        image_urls_medium (:obj:`list` of :obj:`str`): The URL of the medium version of each page.
            This only applies to `ILLUST` and `MANGA`.
        frame_delays (:obj:`list` of :obj:`int`): The duration of each frame in milliseconds.
            This only applies to `UGOIRA`.
        zip_url (str): The URL of the ZIP file containing all frames.
            This only applies to `UGOIRA`.
        tags (:obj:`list` of :obj:`str`): The tags of the illustration.
        tools (:obj:`list` of :obj:`str`): The tools the author used to create the illustration.
        total_bookmarks (int): The number of times this illustration was bookmarked (both public and non-public).
        total_comments (int): The number of comments on this illustration.
        total_view (int): The number of times this illustration was viewed.
    """

    id: int = None
    user: User = None
    create_date: datetime = None

    title: str = None
    caption: str = None
    series: Series = None
    type: Type = None
    age_limit: AgeLimit = None

    width: int = None
    height: int = None

    page_count: int = None
    image_urls: List[str] = attr.Factory(list)
    image_urls_large: List[str] = attr.Factory(list)
    image_urls_medium: List[str] = attr.Factory(list)
    frame_delays: List[int] = attr.Factory(list)
    zip_url: str = None

    tags: List[str] = attr.Factory(list)
    tools: List[str] = attr.Factory(list)

    total_bookmarks: int = None
    total_comments: int = None
    total_view: int = None


__all__ = (
    'User',
    'Series',
    'Type',
    'AgeLimit',
    'Illust',
)
