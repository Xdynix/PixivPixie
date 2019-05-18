# PixivPixie

User-friendly Pixiv API based on [PixivPy](https://github.com/upbit/pixivpy)

## Installation

```shell
pip install PixivPixie --upgrade
```

## Disclaimer

This project is for learning and communication only. It is **NOT** recommended to
use it in large-scale. High-frequency queries will add pressure to the server. Please
support [Pixiv Premium](https://www.pixiv.net/premium.php) if you can.

免责声明：本项目仅用于学习与交流。作者**不鼓励**大规模使用。频繁访问会对服务器带来压力。
请尽量支持[Pixiv高级会员](https://www.pixiv.net/premium.php)。

## About

`PixivPy` is rather a powerful Pixiv API. But its responses are raw json and need
further processing before being used. And both `PublicAPI` and `AppAPI` has its pros and
cons.

This package is designed to serve as a proxy API for `PixivPy`. User can just
fetch illusts they want and doesn't need to think about trifles like paging
parameters or response's json structure.

My main motivation is to write a pixiv crawler to download images. So unrelated APIs are not implemented.
It's welcome to help me implement those APIs.

P.S. English and Chinese discussion is OK. Please forgive me for the poor
English. Fixing typo is also welcome.
