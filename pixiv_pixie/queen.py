from concurrent.futures import ThreadPoolExecutor
from functools import wraps
from itertools import count

from .pixie import PixivPixie


class FunctionCall:
    def __init__(self, fn, *args, **kwargs):
        self.fn = fn
        self.args = args
        self.kwargs = kwargs

    def __str__(self):
        if hasattr(self.fn, '__name__'):
            function_name = self.fn.__name__
        else:
            function_name = repr(self.fn)

        args_str = ', '.join(map(repr, self.args))
        kwargs_str = ', '.join(
            '{}={}'.format(k, repr(v))
            for k, v in self.kwargs.items()
        )

        if args_str and kwargs_str:
            parameter_str = '{}, {}'.format(args_str, kwargs_str)
        elif args_str:
            parameter_str = args_str
        elif kwargs_str:
            parameter_str = kwargs_str
        else:
            parameter_str = ''

        return '{}({})'.format(function_name, parameter_str)

    def __call__(self):
        return self.fn(*self.args, **self.kwargs)


def _submit(func):
    @wraps(func)
    def new_func(self, *args, **kwargs):
        return self.submit(func, self, *args, **kwargs)

    return new_func


class PixieQueen(PixivPixie):
    """Multi-thread Pixiv spider."""

    def __init__(self, max_workers=5, auto_re_login=True, **requests_kwargs):
        super().__init__(auto_re_login=auto_re_login, **requests_kwargs)

        self._executor = ThreadPoolExecutor(max_workers=max_workers)

    def __enter__(self):
        """Wrap of ThreadPoolExecutor.__enter__()."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Wrap of ThreadPoolExecutor.__exit__()."""
        self.shutdown(wait=True)
        return False

    def submit(self, fn, *args, **kwargs):
        """Wrap of ThreadPoolExecutor.submit()."""
        return self._executor.submit(fn, *args, **kwargs)

    def shutdown(self, wait=True):
        """Wrap of ThreadPoolExecutor.shutdown()."""
        self._executor.shutdown(wait=wait)

    @_submit
    def download(self, *args, **kwargs):
        """Similar to PixivPixie.download(), but will returns a Future object.
        """
        return super().download(*args, **kwargs)

    @_submit
    def fetch_and_download(
            self,
            # source
            fetch_func, args=None, kwargs=None,
            # task setting
            max_tries=1,
            # filter
            order_by=None,
            limit_before=None,
            filter_q=None, exclude_q=None,
            limit_after=None,
            # download
            **download_kwargs
    ):
        """Fetch illusts from a query set and download them.

        Args:
            fetch_func: Function that will return a QuerySet of PixivIllust.
            args: Positional arguments of fetch_func.
            kwargs: Keyword arguments of fetch_func.
            max_tries: Max try times when fetch failed. If max_tries=None, it
                will loop infinitely until finished.
            order_by: Arguments that will be passed to QuerySet.order_by().
            limit_before: Number limitation before filtering.
            filter_q: Q object that will be passed to QuerySet.filter().
            exclude_q: Q object that will be passed to QuerySet.exclude() if
                filter_q is not defined.
            limit_after: Number limitation after filtering.
            download_kwargs: Keyword arguments that will be passed to
                PixivPixie.download().

        Returns:
            A Future object. The result of Future object is a list of
                tuple(illust, future).
        """
        if args is None:
            args = []
        if kwargs is None:
            kwargs = {}

        fetch = FunctionCall(fetch_func, *args, **kwargs)

        futures = []

        for tries in count(start=1):
            try:
                qs = fetch()

                if order_by is not None:
                    qs = qs.order_by(*order_by)

                if limit_before is not None:
                    qs = qs.limit(limit_before)

                if filter_q is not None:
                    qs = qs.filter(filter_q)
                elif exclude_q is not None:
                    qs = qs.exclude(exclude_q)

                if limit_after is not None:
                    qs = qs.limit(limit_after)

                for order, illust in qs.enumerate(start=1):
                    kwargs = download_kwargs.copy()
                    kwargs['illust'] = illust
                    if kwargs.get('addition_naming_info') is None:
                        kwargs['addition_naming_info'] = {
                            'order': order,
                        }

                    futures.append((illust, self.download(**kwargs)))

                return futures
            except Exception as e:
                if max_tries is None or tries < max_tries:
                    continue

                e.fetch_call = fetch
                raise
