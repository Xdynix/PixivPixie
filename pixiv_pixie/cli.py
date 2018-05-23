import argparse
from collections import OrderedDict
from concurrent.futures import as_completed
import logging
import os
import sys

import dateutil.parser

from .constants import RankingMode, SearchMode, IllustType
from .exceptions import Error as PixieError
from .queen import PixieQueen
from .utils import with_interval, Q
from .utils.query_set import query_set

logger = logging.getLogger(__name__)

NAME = 'PixivPixieCLI'

RANK_MODE = OrderedDict([
    ('day', RankingMode.DAY),
    ('week', RankingMode.WEEK),
    ('month', RankingMode.MONTH),
    ('day_male', RankingMode.DAY_MALE),
    ('day_female', RankingMode.DAY_FEMALE),
    ('week_original', RankingMode.WEEK_ORIGINAL),
    ('week_rookie', RankingMode.WEEK_ROOKIE),
    ('day_manga', RankingMode.DAY_MANGA),
    ('day_r18', RankingMode.DAY_R18),
    ('day_male_r18', RankingMode.DAY_MALE_R18),
    ('day_female_r18', RankingMode.DAY_FEMALE_R18),
    ('week_r18', RankingMode.WEEK_R18),
    ('week_r18g', RankingMode.WEEK_R18G),
])

SEARCH_MODE = OrderedDict([
    ('text', SearchMode.TEXT),
    ('tag', SearchMode.TAG),
    ('exact_tag', SearchMode.EXACT_TAG),
    ('caption', SearchMode.CAPTION),
])

ILLUST_TYPE = OrderedDict([
    ('illust', IllustType.ILLUST),
    ('manga', IllustType.MANGA),
    ('ugoira', IllustType.UGOIRA),
])


def config_logger():
    logger.setLevel(logging.DEBUG)

    handler = logging.FileHandler(
        'errors.log',
        mode='w',
        encoding='utf-8',
    )
    handler.setLevel(logging.ERROR)
    handler.setFormatter(logging.Formatter(
        fmt='%(asctime)s %(name)-8s %(levelname)-8s %(message)s',
        datefmt='%y-%m-%d %H:%M:%S',
    ))

    logger.addHandler(handler)


def get_parser():
    parser = argparse.ArgumentParser(
        prog=NAME,
        formatter_class=argparse.RawTextHelpFormatter,
        description='PixivPixie CLI',
    )

    parser.add_argument('-p', '--proxy', nargs=1,
                        help='Configure proxy server. e.g.: -p 127.0.0.1:1080')
    parser.add_argument('-U', '--username', required=True, help='Username.')
    parser.add_argument('-P', '--password', required=True, help='Password.')
    parser.add_argument('-w', '--worker', type=int, default=5,
                        help='Worker number.')

    parser.add_argument('--max-tries', type=int, default=5,
                        help='Max try times when fetch failed. '
                             'Set to 0 to try infinitely.')

    parser.add_argument('-t', '--task', required=True, metavar='TASK',
                        choices=[
                            'illust',
                            'following',
                            'user',
                            'ranking',
                            'search',
                            'related',
                        ],
                        help='Task type. Available types:\n'
                             '    illust: Download a single illust.\n'
                             '    following: Download illusts of following '
                             'users.\n'
                             '    user: Download illusts of specific user(s).\n'
                             '    ranking: Download illusts by ranking.\n'
                             '    search: Download illusts by searching.\n'
                             '    related: Download related illusts of '
                             'specific one.\n')
    parser.add_argument('-i', '--illust-id', type=int,
                        help='Illust ID. Only used in \'illust\' and '
                             '\'related\' task.')
    parser.add_argument('-u', '--user-id', type=int, nargs='+',
                        help='User ID(s). Only used in \'user\' task.')
    parser.add_argument('-r', '--rank-mode', metavar='RANK_MODE',
                        choices=list(RANK_MODE.keys()), default='day',
                        help='Rank mode. Could be:\n' +
                             ''.join(
                                 '    {}\n'.format(mode)
                                 for mode in RANK_MODE.keys()
                             ) + 'Default is \'day\'. '
                                 'Only used in \'ranking\' task.')
    parser.add_argument('-a', '--rank-date', type=dateutil.parser.parse,
                        help='Rank date. Only used in \'ranking\' task.')
    parser.add_argument('-q', '--query', nargs='+',
                        help='Search query. Only used in \'search\' task.')
    parser.add_argument('-s', '--search-mode', metavar='SEARCH_MODE',
                        choices=list(SEARCH_MODE.keys()), default='tag',
                        help='Search mode. Could be:\n' +
                             ''.join(
                                 '    {}\n'.format(mode)
                                 for mode in SEARCH_MODE.keys()
                             ) + 'Default is \'tag\'. '
                                 'Only used in \'search\' task.')

    parser.add_argument('--sort-by-bookmark', action='store_true',
                        help='Sort illusts by bookmark number(descending).')
    parser.add_argument('-l', '--limit', type=int, help='Number limitation.')
    parser.add_argument('--no-r18', action='store_true',
                        help='Exclude R-18 illusts.')
    parser.add_argument('--exclude-tag', nargs='*',
                        help='Tag blacklist.')
    parser.add_argument('--exclude-user-id', nargs='*',
                        help='User blacklist.')
    parser.add_argument('--min-width', type=int)
    parser.add_argument('--max-width', type=int)
    parser.add_argument('--min-height', type=int)
    parser.add_argument('--max-height', type=int)
    parser.add_argument('--min-aspect-ratio', type=float)
    parser.add_argument('--max-aspect-ratio', type=float)
    parser.add_argument('--earliest', type=dateutil.parser.parse,
                        help='Earliest date of illust. Earlier illust will be '
                             'ignored.')
    parser.add_argument('--type',
                        choices=list(ILLUST_TYPE.keys()),
                        help='Illust type. Could be:\n' +
                             ''.join(
                                 '    {}\n'.format(t)
                                 for t in ILLUST_TYPE.keys()
                             ))

    parser.add_argument('-d', '--dir', default=os.path.curdir,
                        help='Download directory path.')
    parser.add_argument('-n', '--name',
                        help='File naming rule with the syntax of python '
                             'formatter\n'
                             'string. The following parameters can be used:\n'
                             '    illust.illust_id\n'
                             '    illust.title\n'
                             '    illust.width\n'
                             '    illust.height\n'
                             '    illust.user_id\n'
                             '    illust.user_name\n'
                             '    illust.total_bookmarks\n'
                             '    illust.rank\n'
                             '    page: 0-based page number.\n'
                             '    original_name: The default filename.\n'
                             '    root: The root part of original_name.\n'
                             '    ext: The extension part of original_name.\n'
                             '    order: 1-based ordinal.\n')
    parser.add_argument('--no-convert', action='store_true',
                        help='Do not convert ugoira to GIF file.')
    parser.add_argument('--replace', action='store_true',
                        help='Replace existed file(s)')
    parser.add_argument('--check-exists', nargs='*', metavar='PATH',
                        help='Addition path(s) to check whether the illust '
                             'exists (by\nname).')
    return parser


def get_filter_option(args):
    option = {}

    if args.sort_by_bookmark:
        option['order_by'] = ['-total_bookmarks']
    if args.limit:
        option['limit_after'] = args.limit

    if args.exclude_tag:
        tag_black_list = args.exclude_tag
    else:
        tag_black_list = []
    if args.exclude_user_id:
        user_black_list = args.exclude_user_id
    else:
        user_black_list = []
    if args.no_r18:
        tag_black_list.append('R-18')
        tag_black_list.append('R-18G')

    exclude_q = ~Q()
    for tag in tag_black_list:
        exclude_q = exclude_q | Q(tags__contains=tag)
    for user in user_black_list:
        exclude_q = exclude_q | Q(user_id=user)
    option['exclude_q'] = exclude_q

    filter_q = Q()
    if args.min_width is not None:
        filter_q = filter_q & Q(width__gte=args.min_width)
    if args.max_width is not None:
        filter_q = filter_q & Q(width__lte=args.max_width)
    if args.min_height is not None:
        filter_q = filter_q & Q(height__gte=args.min_height)
    if args.max_height is not None:
        filter_q = filter_q & Q(height__lte=args.max_height)
    if args.min_aspect_ratio is not None:
        filter_q = filter_q & Q(aspect_ratio__gte=args.min_aspect_ratio)
    if args.max_aspect_ratio is not None:
        filter_q = filter_q & Q(aspect_ratio__lte=args.max_aspect_ratio)
    if args.earliest is not None:
        filter_q = filter_q & Q(creation_time__gte=args.earliest)
    if args.type is not None:
        filter_q = filter_q & Q(type=ILLUST_TYPE[args.type])
    option['filter_q'] = filter_q

    return option


def get_download_kwargs(args):
    return {
        'directory': args.dir,
        'name': args.name,
        'convert_ugoira': not args.no_convert,
        'replace': args.replace,
        'check_exists': args.check_exists,
    }


@with_interval(interval=50)
def show_status(finished, total):
    s = '{finished:>3}/{total:<3}'.format(finished=finished, total=total)
    sys.stdout.write('\r{}'.format(s))
    sys.stdout.flush()


def clear_futures(futures):
    for future in as_completed(futures):
        try:
            future.result()
        except Exception as e:
            logger.error(e)


@query_set
def yield_one_illust(pixie, illust_id):
    yield pixie.illust(illust_id)


def cli(args):
    args.worker = max(1, args.worker)

    if args.max_tries <= 0:
        args.max_tries = None

    requests_kwargs = {
        'timeout': (10, 60),
    }
    if args.proxy:
        requests_kwargs['proxies'] = {
            'http': args.proxy[0],
            'https': args.proxy[0],
        }

    queen = PixieQueen(
        max_workers=args.worker,
        auto_re_login=True,
        **requests_kwargs,
    )

    print('Logging in...')
    queen.login(args.username, args.password)

    filter_option = get_filter_option(args)
    download_kwargs = get_download_kwargs(args)

    # prepare source
    if args.task == 'illust':
        if not args.illust_id:
            raise TypeError('Illust ID is required in \'illust\' task.')

        fetch_func = [yield_one_illust]
        fetch_args = [(queen, args.illust_id)]
    elif args.task == 'following':
        if not args.earliest:
            raise TypeError('Earliest date is required in \'following\' task.')

        fetch_func = [queen.my_following_illusts]
        fetch_args = [(args.earliest,)]
    elif args.task == 'user':
        if not args.user_id:
            raise TypeError('User ID is required in \'user\' task.')

        fetch_func = [queen.user_illusts for _ in args.user_id]
        fetch_args = [(uid,) for uid in args.user_id]
    elif args.task == 'ranking':
        fetch_func = [queen.ranking]
        fetch_args = [(RANK_MODE[args.rank_mode], args.rank_date)]
    elif args.task == 'search':
        if not args.query:
            raise TypeError('Query is required in \'search\' task.')

        fetch_func = [queen.search]
        fetch_args = [(' '.join(args.query), SEARCH_MODE[args.search_mode])]
    elif args.task == 'related':
        if not args.illust_id:
            raise TypeError('Illust ID is required in \'related\' task.')

        if not args.limit:
            raise TypeError('Limit is required in \'related\' task.')

        fetch_func = [queen.related_illusts]
        fetch_args = [(args.illust_id, args.limit)]
    else:
        return

    fetch_futures = []
    download_futures = []
    page_download_futures = []
    finished_download = 0

    def update_status():
        show_status(finished_download, len(page_download_futures))

    def inc_finished_download(*_):
        nonlocal finished_download
        finished_download += 1

        update_status()

    def download_done_callback(download_future):
        for url, path, page_download_future in download_future.result():
            page_download_futures.append(page_download_future)
            page_download_future.add_done_callback(inc_finished_download)

        update_status()

    def submit_download_callback(download_future, _):
        download_futures.append(download_future)
        download_future.add_done_callback(download_done_callback)

        update_status()

    with queen:
        print('Downloading...')

        for fetch_func, fetch_args in zip(fetch_func, fetch_args):
            fetch_futures.append(queen.fetch_and_download(
                fetch_func, args=fetch_args,
                max_tries=args.max_tries,
                submit_download_callback=submit_download_callback,
                **filter_option,
                **download_kwargs,
            ))

        clear_futures(fetch_futures)
        clear_futures(download_futures)
        clear_futures(page_download_futures)

    print('\nDone.')


def main():
    config_logger()
    try:
        parser = get_parser()
        args = parser.parse_args()

        cli(args)
    except (TypeError, PixieError) as e:
        print(e)
        logger.error(e)
    except Exception as e:
        print('Unhandled exception detected! '
              'Please contact author and attached with log file!')
        logger.fatal('Unhandled exception: {}'.format(e))
        logger.exception(e)
