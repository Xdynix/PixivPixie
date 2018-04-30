import datetime

import dateutil.parser

from .constants import IllustType, IllustAgeLimit
from pixiv_pixie.utils import LazyProperty


def _lazy(attr_name):
    def get_func(self):
        self.update()
        return getattr(self, attr_name)

    return LazyProperty(get_func, property_name=attr_name)


class PixivIllust:
    """Pixiv Illust object.

    Used to access illust info.

    Attributes:
        illust_id: Illust ID.
        title: Title.
        caption: Some description text. May contains HTML tags or escape
            characters.
        creation_time: A datetime object.
        width: Width.
        height: Height.
        image_urls: A list of original image urls. A ugoira's image_urls will
            only contains one URL of a ZIP file which contains all frames.
        frame_delays: None for non-ugoira illust. Or a list of delay durations
            in microsecond.
        type: Illust type. Will be ILLUST, MANGA or UGOIRA. (These constants are
            defined in pixiv_pixie.constants.illust.)
        age_limit: Age limitation type. Will be ALL_AGE, R18 or R18G. (These
            constants are defined in pixiv_pixie.constants.illust.)
        tags: Tags.
        tools: Tools used be the author.
        user_account: The author's account name.
        user_id: The author's user ID.
        user_name: The author's nickname.
        total_bookmarks: The number bookmarks on this illust.
        total_view: The number of times this illust been viewed.
        rank: Ranking number of the illust. Only make sense when the illust was
            fetched from ranking. Starting from 1.
    """

    title = _lazy('title')
    caption = _lazy('caption')
    creation_time = _lazy('creation_time')

    width = _lazy('width')
    height = _lazy('height')

    image_urls = _lazy('image_urls')
    frame_delays = _lazy('frame_delays')

    type = _lazy('type')
    age_limit = _lazy('age_limit')

    tags = _lazy('tags')
    tools = _lazy('tools')

    user_account = _lazy('user_account')
    user_id = _lazy('user_id')
    user_name = _lazy('user_name')

    total_bookmarks = _lazy('total_bookmarks')
    total_view = _lazy('total_view')

    @classmethod
    def from_papi(cls, pixie, json_result):
        illust = cls(pixie=pixie, illust_id=json_result.id)
        illust.update_from_papi(json_result)
        return illust

    @classmethod
    def from_aapi(cls, pixie, json_result):
        illust = cls(pixie=pixie, illust_id=json_result.id)
        illust.update_from_aapi(json_result)
        return illust

    def __init__(self, pixie, illust_id):
        self.pixie = pixie
        self.illust_id = illust_id

        self.rank = None

    def __repr__(self):
        return 'PixivIllust(illust_id={})'.format(self.illust_id)

    @property
    def size(self):
        """A tuple of (width, height)."""
        return self.width, self.height

    @property
    def area(self):
        """Area in pixels."""
        return self.width * self.height

    @property
    def aspect_ratio(self):
        """Width divided by height."""
        if self.height == 0:
            return 0
        return self.width / self.height

    @property
    def page_count(self):
        """The number of pages."""
        return len(self.image_urls)

    def update(self):
        illust = self.pixie.illust(self.illust_id)

        attributes = [
            'illust_id',
            'title',
            'caption',
            'creation_time',
            'width',
            'height',
            'image_urls',
            'frame_delays',
            'type',
            'age_limit',
            'tags',
            'tools',
            'user_account',
            'user_id',
            'user_name',
            'total_bookmarks',
            'total_view',
            'rank',
        ]

        for attr in attributes:
            value = getattr(illust, attr)
            if isinstance(value, list):
                value = value.copy()
            setattr(self, attr, value)

    def update_from_papi(self, json_result):
        self.illust_id = json_result.id
        self.title = json_result.title
        if json_result.caption is not None:
            self.caption = json_result.caption
        else:
            self.caption = ''
        self.creation_time = datetime.datetime.strptime(
            json_result.created_time,
            '%Y-%m-%d %H:%M:%S',
        )

        self.width = json_result.width
        self.height = json_result.height

        if json_result.page_count == 1:
            if json_result.type == 'ugoira':  # ugoira
                if json_result.metadata is not None:
                    self.image_urls = [
                        json_result.metadata.zip_urls.ugoira600x600,
                    ]
                    self.frame_delays = [
                        frame.delay_msec
                        for frame in json_result.metadata.frames
                    ]
            else:  # single page illust
                self.image_urls = [json_result.image_urls.large]
                self.frame_delays = None
        else:  # multi page illust
            if json_result.metadata is not None:
                self.image_urls = [
                    page.image_urls.large
                    for page in json_result.metadata.pages
                ]
            self.frame_delays = None

        self.type = {
            'illustration': IllustType.ILLUST,
            'manga': IllustType.MANGA,
            'ugoira': IllustType.UGOIRA,
        }[json_result.type]
        self.age_limit = {
            'all-age': IllustAgeLimit.ALL_AGE,
            'r18': IllustAgeLimit.R18,
            'r18-g': IllustAgeLimit.R18G,
        }[json_result.age_limit]

        self.tags = [tag for tag in json_result.tags]
        if json_result.tools is not None:
            self.tools = [tool for tool in json_result.tools]

        self.user_account = json_result.user.account
        self.user_id = json_result.user.id
        self.user_name = json_result.user.name

        favorited_count = json_result.stats.favorited_count
        if favorited_count.public is not None:
            self.total_bookmarks = sum(favorited_count.values())
        self.total_view = json_result.stats.views_count

    def update_from_aapi(self, json_result):
        self.illust_id = json_result.id
        self.title = json_result.title
        self.caption = json_result.caption
        self.creation_time = dateutil.parser.parse(json_result.create_date)

        self.width = json_result.width
        self.height = json_result.height

        if json_result.page_count == 1 and json_result.type != 'ugoira':
            # single page illust
            self.image_urls = [
                json_result.meta_single_page.original_image_url
            ]
            self.frame_delays = None
        elif json_result.page_count > 1:  # multi page illust
            self.image_urls = [
                page.image_urls.original
                for page in json_result.meta_pages
            ]
            self.frame_delays = None
        else:  # ugoira
            pass

        self.type = {
            'illust': IllustType.ILLUST,
            'manga': IllustType.MANGA,
            'ugoira': IllustType.UGOIRA,
        }[json_result.type]

        self.tags = [tag.name for tag in json_result.tags]
        self.tools = [tool for tool in json_result.tools]

        if 'R-18' in self.tags:
            self.age_limit = IllustAgeLimit.R18
        elif 'R-18G' in self.tags:
            self.age_limit = IllustAgeLimit.R18G
        else:
            self.age_limit = IllustAgeLimit.ALL_AGE

        self.user_account = json_result.user.account
        self.user_id = json_result.user.id
        self.user_name = json_result.user.name

        self.total_bookmarks = json_result.total_bookmarks
        self.total_view = json_result.total_view
