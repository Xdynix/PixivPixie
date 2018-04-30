from datetime import datetime, timedelta
from functools import partial, wraps
from threading import Lock

import requests


def download(file, url, can_cancel=False, chunk_size=1024, **requests_kwargs):
    with requests.get(url, **requests_kwargs) as response:
        response.raise_for_status()

        wrote_size = 0
        if 'Content-Length' in response.headers:
            total_size = int(response.headers['Content-Length'])
        else:
            total_size = None

        for chunk in response.iter_content(chunk_size=chunk_size):
            should_continue = yield wrote_size, total_size

            if can_cancel and not should_continue:
                break

            wrote_size += len(chunk)
            file.write(chunk)

        yield wrote_size, total_size


def safe_callback(func=None, *, logger=None):
    if func is None:
        return partial(safe_callback, logger=logger)

    @wraps(func)
    def new_func(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if logger is not None:
                logger.error('Unhandled exception in callback.')
                logger.exception(e)

    return new_func


class FunctionWithInterval:
    def __init__(self, func, interval):
        if isinstance(interval, (float, int)):
            interval = timedelta(microseconds=interval)

        self._func = func
        self._interval = interval

        self._lock = Lock()
        self._last_call = None

        wraps(func)(self)

    def __call__(self, *args, **kwargs):
        with self._lock:
            interval = self._interval
            last_call = self._last_call
            current_time = datetime.now()

            if last_call is not None and last_call + interval > current_time:
                return

            self._last_call = current_time

        self._func(*args, **kwargs)


def with_interval(func=None, *, interval=0):
    if func is None:
        return partial(with_interval, interval=interval)

    return FunctionWithInterval(func, interval)
