# PixivPixie

User-friendly Pixiv API based on
[PixivPy](https://github.com/upbit/pixivpy)

## Disclaimer 免责声明

This project is for learning and communication only. It is **NOT** recommended to
use it in large-scale. High-frequency queries will add pressure to the server. Please
support [Pixiv Premium](https://www.pixiv.net/premium.php) if you can.

本项目仅用于学习与交流。作者**不鼓励**大规模使用。频繁访问会对服务器带来压力。
请尽量支持[Pixiv高级会员](https://www.pixiv.net/premium.php)。

## About

`PixivPy` is rather a powerful Pixiv API. But its response are raw json and need
further processing before used. And both `PublicAPI` and `AppAPI` has its pros and
cons.

This package is designed to serve as a proxy API for `PixivPy`. User can just
fetch illusts they want and doesn't need to think about trifles like paging
parameters or response's json structure.

My main motivation is to write a pixiv crawler to download images. So unrelated APIs are not implemented.
It's welcome to help me implement those APIs.

P.S. English and Chinese discussion is OK. Please forgive me for the poor
English. Fixing typo is also welcome.

## Usage

### Basic

The `PixivPixie` class provides core functions.

```python
from pixiv_pixie import PixivPixie

requests_kwargs = {
    # You may need to use proxies.
    # 'proxies': {
    #     'https': 'http://127.0.0.1:8888',
    #  },
    # PixivPy's PAPI use https, an easy way is disable requests SSL verify.
    # 'verify': False,
}


def print_illusts(illusts, limit=10):
    try:
        for idx, illust in enumerate(illusts):
            if limit is not None and idx >= limit:
                break
            print(
                '{:4}'.format(idx),
                '{:8}'.format(illust.illust_id),
                '{:>4}×{:<4}'.format(illust.width, illust.height),
                illust.title,
                sep=' | ',
            )
    except Exception as e:
        print(e)


def main():
    pixie = PixivPixie(**requests_kwargs)

    # You MUST login first.
    # Replace it with your own account.
    pixie.login('username', 'password')

    # Fetch single illust
    illust = pixie.illust(63808518)
    print_illusts([illust])

    # Fetch following users' new illusts
    print_illusts(pixie.my_following_illusts())

    # Fetch user's illusts
    print_illusts(pixie.user_illusts(2188232))

    # Fetch ranking illusts
    print_illusts(pixie.ranking())

    # Search illusts
    print_illusts(pixie.search('オリジナル'), limit=50)

    # Fetch related illusts
    print_illusts(pixie.related_illusts(63808518), limit=50)

    # Download illust
    pixie.download_illust(illust, directory='download')

    # Download ugoira and manually convert it
    illust = pixie.illust(64421170)
    pixie.download_illust(
        illust, directory='download', name='ugoira{ext}',
        convert_ugoira=False,
    )
    pixie.convert_zip_to_gif(
        os.path.join('download', 'ugoira.zip'),
        frame_delays=illust.frame_delays,
    )


if __name__ == '__main__':
    main()
```

### Make queries and `Q` object

```python
from pixiv_pixie import PixivPixie, Q


def main():
    pixie = PixivPixie()
    pixie.login('username', 'password')  # Replace it with your own.

    for illust in pixie.search('オリジナル') \
            .exclude(tags__contains='R-18') \
            .order_by('-total_bookmarks') \
            .limit(10):
        pixie.download(illust)

    # You can use Q object to perform more complex filtering.
    for illust in pixie.search('オリジナル') \
            .filter(
                ~Q(tags__contains='R-18')
                & (Q(aspect_ratio__lt=1) | Q(type=UGOIRA))
            ) \
            .order_by('-total_bookmarks') \
            .limit(10):
        pixie.download(illust)


if __name__ == '__main__':
    main()
```

### Downloader

```python
import os
from time import sleep

from pixiv_pixie import PixivPixie, Downloader, TaskStatus

requests_kwargs = {
    'proxies': {
        # 'https': 'http://127.0.0.1:1080',
    },
    # 'verify': False,
}


def main():
    pixie = PixivPixie(**requests_kwargs)
    print('Logging in...')
    pixie.login('username', 'password')
    manager = Downloader(pixie)
    for uid in [7703097, 19898964]:
        manager.add_fetch_task(
            pixie.user_illusts(uid), name='uid={}'.format(uid),
            directory=os.path.join('download', 'uid={}'.format(uid)),
        )

    manager.queue.spawn_workers(5)
    while not manager.all_done():
        update(manager.status())
        sleep(0.1)
    manager.queue.halt_workers()

    with open('temp2_error.log', 'wt', encoding='utf-8') as f:
        status = manager.status()
        for record in status:
            if record.exception:
                print('Error in task:', record.name, file=f)
                print(str(record.exception), file=f)
            children_exceptions = [
                child.exception for child in record.children if child.exception
            ]
            if children_exceptions:
                print('Error in children:', record.name, file=f)
                for exception in children_exceptions:
                    print(str(exception), file=f)


def update(status):
    os.system('cls' if os.name == 'nt' else 'clear')
    for record in status:
        name = record.name
        status = record.status.value
        exception = str(record.exception)
        children_num = len(record.children)
        children_done_num = 0
        children_error_num = 0
        for child in record.children:
            if child.status in [TaskStatus.FAILURE, TaskStatus.SUCCESS]:
                children_done_num += 1
            if child.exception is not None:
                children_error_num += 1
        print(
            '{name:15} | '
            '{status:7} | '
            '{children_error_num:3}/{children_done_num:3}/{children_num:3} | '
            '{exception}'.format(
                name=name, status=status, exception=exception,
                children_num=children_num,
                children_done_num=children_done_num,
                children_error_num=children_error_num,
            )
        )


if __name__ == '__main__':
    main()
```
