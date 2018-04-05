from enum import Enum


class IllustType(Enum):
    ILLUST = 'illust'
    MANGA = 'manga'
    UGOIRA = 'ugoira'


class IllustAgeLimit(Enum):
    ALL_AGE = 'all-age'
    R18 = 'r18'
    R18G = 'r18g'


class RankingMode(Enum):
    DAY = 'day'
    WEEK = 'week'
    MONTH = 'month'
    DAY_MALE = 'day_male'
    DAY_FEMALE = 'day_female'
    WEEK_ORIGINAL = 'week_original'
    WEEK_ROOKIE = 'week_rookie'
    DAY_MANGA = 'day_manga'
    DAY_R18 = 'day_r18'
    DAY_MALE_R18 = 'day_male_r18'
    DAY_FEMALE_R18 = 'day_female_r18'
    WEEK_R18 = 'week_r18'
    WEEK_R18G = 'week_r18g'


class SearchMode(Enum):
    TEXT = 'text'
    TAG = 'tag'
    EXACT_TAG = 'exact_tag'
    CAPTION = 'caption'


class SearchPeriod(Enum):
    ALL = 'all'
    DAY = 'day'
    WEEK = 'week'
    MONTH = 'month'


class SearchOrder(Enum):
    DESC = 'desc'
    ASC = 'asc'
