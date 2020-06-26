# PixivPixie

**This project is under remaking. If you want to browse the old version, please switch to the `master` branch.**

User-friendly Pixiv API based on [PixivPy](https://github.com/upbit/pixivpy)

## Installation

```shell script
pip install --upgrade PixivPixie
```

## Disclaimer

This project is for learning and communication only. It is **NOT** recommended to use it in large-scale. High-frequency queries
 will add pressure to the server. Please support [Pixiv Premium](https://www.pixiv.net/premium.php) if you can.

免责声明：本项目仅用于学习与交流。作者**不鼓励**大规模使用。频繁访问会对服务器带来压力。 请尽量支持
[Pixiv高级会员](https://www.pixiv.net/premium.php)。

## About

`PixivPy` is rather a powerful Pixiv API. But its responses are raw json and need further processing before being used. And
both `PublicAPI` and `AppAPI` has its pros and cons.

This package is designed to serve as a proxy API for `PixivPy`. User can just fetch illustrations they want and doesn't need to
think about trifles like paging parameters or response's json structure.

My main motivation is to write a pixiv crawler to download images. So unrelated APIs are not implemented. It's welcome to help
me implement those APIs.

P.S. English and Chinese discussion is OK. Please forgive me for the poor English. Fixing typo is also welcome.

## Development

```shell script
git clone https://github.com/Xdynix/PixivPixie.git
cd PixivPixie

# Setup and activate virtualenv.
virtualenv venv  # Please use the name `venv`, otherwise the configuration file may not work properly.
.\venv\Scripts\activate  # On Windows environment.
source venv/bin/activate  # On POSIX (Linux/MacOS/Other) environment.

pip install -r requirements.txt
pip install -r requirements-dev.txt
pip install -e .
pre-commit install
```

To run tests, simply use command `pytest`.

---

To run web tests, which which will check the availability of Pixiv's API and the schema of the response data, you need to first
create the file `secret.json` in the root directory of the project, and fill in the account information you will use for
testing in the following format:

```json
{
  "password": "pa33w0rd",
  "requests_kwargs": {},
  "username": "foobar@example.com"
}
```

Then use command `pytest webtests` to run web tests.
