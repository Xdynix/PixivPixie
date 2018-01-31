import datetime

import dateutil.parser

from .constants import illust as illust_constants


class PixivIllust(object):
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

    def __init__(self):
        self.illust_id = 0
        self.title = ''
        self.caption = ''
        self.creation_time = None

        self.width = 0
        self.height = 0

        self.image_urls = []
        self.frame_delays = None

        self.type = illust_constants.ILLUST
        self.age_limit = illust_constants.ALL_AGE

        self.tags = []
        self.tools = []

        self.user_account = ''
        self.user_id = 0
        self.user_name = ''

        self.total_bookmarks = 0
        self.total_view = 0

        self.rank = 0

    def __repr__(self):
        return '<PixivIllust illust_id={}>'.format(self.illust_id)

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

    @classmethod
    def from_papi(cls, json_result):
        illust = cls()

        illust.illust_id = json_result.id
        illust.title = json_result.title
        illust.caption = json_result.caption
        illust.creation_time = datetime.datetime.strptime(
            json_result.created_time,
            '%Y-%m-%d %H:%M:%S',
        )

        illust.width = json_result.width
        illust.height = json_result.height

        if json_result.metadata is None:  # single page illust
            illust.image_urls.append(json_result.image_urls.large)
        elif json_result.page_count > 1:  # multi page illust
            for page in json_result.metadata.pages:
                illust.image_urls.append(page.image_urls.large)
        else:  # ugoira
            illust.image_urls.append(json_result
                                     .metadata
                                     .zip_urls
                                     .ugoira600x600
                                     # .replace('600x600', '1920x1080')
                                     )
            illust.frame_delays = []
            for frame in json_result.metadata.frames:
                illust.frame_delays.append(frame.delay_msec)

        illust.type = {
            'illustration': illust_constants.ILLUST,
            'manga': illust_constants.MANGA,
            'ugoira': illust_constants.UGOIRA,
        }[json_result.type]
        illust.age_limit = {
            'all-age': illust_constants.ALL_AGE,
            'r18': illust_constants.R18,
            'r18-g': illust_constants.R18G,
        }[json_result.age_limit]

        for tag in json_result.tags:
            illust.tags.append(tag)
        for tool in json_result.tools:
            illust.tools.append(tool)

        illust.user_account = json_result.user.account
        illust.user_id = json_result.user.id
        illust.user_name = json_result.user.name

        illust.total_bookmarks = sum(json_result.stats.favorited_count.values())
        illust.total_view = json_result.stats.views_count

        return illust

    @classmethod
    def from_aapi(cls, json_result):
        illust = cls()

        illust.illust_id = json_result.id
        illust.title = json_result.title
        illust.caption = json_result.caption
        illust.creation_time = dateutil.parser.parse(json_result.create_date)

        illust.width = json_result.width
        illust.height = json_result.height

        if json_result.page_count == 1 and json_result.type != 'ugoira':
            # single page illust
            illust.image_urls.append(
                json_result.meta_single_page.original_image_url)
        elif json_result.page_count > 1:  # multi page illust
            for page in json_result.meta_pages:
                illust.image_urls.append(page.image_urls.original)
        else:  # ugoira
            raise NotImplementedError

        illust.type = {
            'illust': illust_constants.ILLUST,
            'manga': illust_constants.MANGA,
            'ugoira': illust_constants.UGOIRA,
        }[json_result.type]

        for tag in json_result.tags:
            illust.tags.append(tag.name)
        for tool in json_result.tools:
            illust.tools.append(tool)

        if 'R-18' in illust.tags:
            illust.age_limit = illust_constants.R18
        elif 'R-18G' in illust.tags:
            illust.age_limit = illust_constants.R18G
        else:
            illust.age_limit = illust_constants.ALL_AGE

        illust.user_account = json_result.user.account
        illust.user_id = json_result.user.id
        illust.user_name = json_result.user.name

        illust.total_bookmarks = json_result.total_bookmarks
        illust.total_view = json_result.total_view

        return illust
