import argparse
from datetime import datetime
import logging
import os
import sys
from time import sleep

import dateutil.parser

import pixiv_pixie
from pixiv_pixie import PixivPixie, LoginFailed, Q, Downloader, TaskStatus


def main():
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    handler = logging.FileHandler(
        'errors.log',
        mode='w',
        encoding='utf-8',
    )
    handler.setLevel(logging.ERROR)
    handler.setFormatter(logging.Formatter(
        fmt='%(asctime)s %(name)-15s %(levelname)-8s %(message)s',
        datefmt='%y-%m-%d %H:%M:%S',
    ))
    logger.addHandler(handler)

    try:
        parser = get_parser()
        args = parser.parse_args()

        # prepare requests
        requests_kwargs = {
            # 'timeout': (5, 30),
        }
        if args.proxy:
            requests_kwargs['proxies'] = {
                'http': args.proxy[0],
                'https': args.proxy[0],
            }

        pixie = PixivPixie(**requests_kwargs)
        try:
            print('Logging in...')
            pixie.login(args.username, args.password)
        except LoginFailed as e:
            print(e)
            return

        if args.worker <= 0:
            print('At least one worker required.')
            return

        download_kwargs = dict(
            directory=args.dir,
            name=args.name,
            convert_ugoira=not args.no_convert,
            replace=args.replace,
            check_exists=args.check_exists,
        )

        # prepare source
        if args.task == 'illust':
            if not args.illust_id:
                print('Illust ID is required in \'illust\' task.')
                return
            try:
                print('Downloading...')
                pixie.download_illust(args.illust_id, **download_kwargs)
                print('Done.')
                return
            except Exception as e:
                print(e)
                return
        elif args.task == 'following':
            if not args.earliest:
                print('Earliest date is required in \'following\' task.')
                return
            source = pixie.my_following_illusts(args.earliest)
        elif args.task == 'user':
            if not args.user_id:
                print('User ID is required in \'user\' task.')
                return
            source = [pixie.user_illusts(uid) for uid in args.user_id]
        elif args.task == 'ranking':
            source = pixie.ranking(args.rank_mode, args.rank_date)
        elif args.task == 'search':
            if not args.query:
                print('Query is required in \'search\' task.')
                return
            source = pixie.search(' '.join(args.query), args.search_mode)
        elif args.task == 'related':
            if not args.illust_id:
                print('Illust ID is required in \'related\' task.')
                return
            if not args.limit:
                print('Limit is required in \'related\' task.')
                return
            source = pixie.related_illusts(args.illust_id).limit(args.limit)
        else:
            return

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
        exclude_q = Q()
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
            filter_q = filter_q & Q(type=args.type)
        option['filter_q'] = filter_q

        downloader = Downloader(pixie, logger=logger)
        downloader.add_fetch_task(source, **option, **download_kwargs)

        print('Downloading...')
        try:
            downloader.queue.spawn_workers(args.worker)
            start_time = datetime.now()
            while not downloader.all_done():
                update(downloader.status(), start_time)
                sleep(0.5)
            update(downloader.status(), start_time)
        except KeyboardInterrupt:
            raise
        except Exception as e:
            logger.exception(e)
        finally:
            downloader.queue.halt_workers()
        print('\nDone.')
    except Exception as e:
        logger.exception(e)


def update(status, start_time):
    total = 0
    finished = 0
    error = 0
    for record in status:
        if record.exception:
            error += 1
        total += len(record.children)
        for child in record.children:
            if child.exception:
                error += 1
            if child.status in [TaskStatus.FAILURE, TaskStatus.SUCCESS]:
                finished += 1
    used_time = datetime.now() - start_time
    s = '{used_time} {finished:>3}/{total:<3} Error: {error}'.format(
        used_time=used_time,
        finished=finished,
        total=total,
        error=error,
    )
    sys.stdout.write('\r{}'.format(s))
    sys.stdout.flush()


def get_parser():
    parser = argparse.ArgumentParser(
        prog='PixivPixie',
        formatter_class=argparse.RawTextHelpFormatter,
        description='PixivPixie CLI',
    )
    parser.add_argument(
        '-v', '--version', action='version', version=pixiv_pixie.__version__)

    parser.add_argument('-p', '--proxy', nargs=1,
                        help='Configure proxy server. e.g.: -p 127.0.0.1:1080')
    parser.add_argument('-U', '--username', required=True, help='Username.')
    parser.add_argument('-P', '--password', required=True, help='Password.')
    parser.add_argument('-w', '--worker', type=int, default=5,
                        help='Worker number.')

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
                        choices=[
                            'day',
                            'week',
                            'month',
                            'day_male',
                            'day_female',
                            'week_original',
                            'week_rookie',
                            'day_manga',
                            'day_r18',
                            'day_male_r18',
                            'day_female_r18',
                            'week_r18',
                            'week_r18g',
                        ], default='day',
                        help='Rank mode. Could be:\n'
                             '    day(default)\n'
                             '    week\n'
                             '    month\n'
                             '    day_male\n'
                             '    day_female\n'
                             '    week_original\n'
                             '    week_rookie\n'
                             '    day_manga\n'
                             '    day_r18\n'
                             '    day_male_r18\n'
                             '    day_female_r18\n'
                             '    week_r18\n'
                             '    week_r18g\n'
                             'Only used in \'ranking\' task.')
    parser.add_argument('-a', '--rank-date', type=dateutil.parser.parse,
                        help='Rank date. Only used in \'ranking\' task.')
    parser.add_argument('-q', '--query', nargs='+',
                        help='Search query. Only used in \'search\' task.')
    parser.add_argument('-s', '--search-mode', metavar='SEARCH_MODE',
                        choices=[
                            'text',
                            'tag',
                            'exact_tag',
                            'caption',
                        ], default='tag',
                        help='Search mode. Could be:\n'
                             '    text\n'
                             '    tag(default)\n'
                             '    exact_tag\n'
                             '    caption\n'
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
                        choices=[
                            'illust',
                            'manga',
                            'ugoira',
                        ],
                        help='Illust type. Could be:\n'
                             '    illust\n'
                             '    manga\n'
                             '    ugoira\n')

    parser.add_argument('-d', '--dir', default=os.curdir,
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


if __name__ == '__main__':
    main()
