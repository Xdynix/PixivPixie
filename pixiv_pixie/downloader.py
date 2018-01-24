from itertools import chain
from threading import Lock

from .utils.datatypes import JsonDict, JsonArray
from .utils.query_set import QuerySet
from .utils.task_queue import TaskQueue, TaskStatus


class Downloader:
    """A simple multi-thread downloader."""
    def __init__(self, pixie):
        self._pixie = pixie

        self._queue = TaskQueue()
        self._lock = Lock()
        self._records = []

    @property
    def pixie(self):
        return self._pixie

    @property
    def queue(self):
        return self._queue

    def add_fetch_task(
            self, source, name=None,
            order_by=None,
            limit_before=None,
            filter_q=None, exclude_q=None,
            limit_after=None,
            **download_kwargs
    ):
        """Add a task.

        Args:
            source: Generator that will yield PixivIllust. Or a list of
                generator that will yield PixivIllust.
            name: Name of the task.
            order_by: Arguments that will be passed to QuerySet.order_by().
            limit_before: Number limitation before filtering.
            filter_q: Q object that will be passed to QuerySet.filter().
            exclude_q: Q object that will be passed to QuerySet.exclude() if
                filter_q is not defined.
            limit_after: Number limitation after filtering.
            download_kwargs: Keyword arguments that will be passed to
                PixivPixie.download().
        """
        kwargs = dict(
            order_by=order_by,
            limit_before=limit_before,
            filter_q=filter_q, exclude_q=exclude_q,
            limit_after=limit_after,
        )
        kwargs.update(**download_kwargs)

        with self._lock:
            if name is None:
                name = 'Task {}'.format(len(self._records) + 1)
            record = _TaskRecord(name)
            result = self.queue.enqueue(
                self._fetch,
                args=(source, record),
                kwargs=kwargs,
            )
            record.result = result
            self._records.append(record)

    def status(self):
        """Current status of all tasks.

        Return an array with following structure:
        [
            {
                'name': 'Task 1',
                'status': STATUS,
                'exception': None,
                'children': [
                    {
                        'illust_id': 12345678,
                        'status': STATUS,
                        'exception': None,
                    },
                    # ...
                ],
            },
            # ...
        ]
        Task status is an instance of TaskStatus.
        """
        status = JsonArray()
        with self._lock:
            for record in self._records:
                status.append(JsonDict(
                    name=record.name,
                    status=record.result.status,
                    exception=record.result.exception,
                    children=JsonArray(JsonDict(
                        illust_id=illust.illust_id,
                        status=child_result.status,
                        exception=child_result.exception,
                    ) for illust, child_result in record.children)
                ))
        return status

    def all_done(self):
        status = self.status()
        for record in status:
            if record.status not in [TaskStatus.FAILURE, TaskStatus.SUCCESS]:
                return False
            for child in record.children:
                if child.status not in [TaskStatus.FAILURE, TaskStatus.SUCCESS]:
                    return False
        return True

    def _fetch(
            self, source, record_obj,
            order_by=None,
            limit_before=None,
            filter_q=None, exclude_q=None,
            limit_after=None,
            **download_kwargs
    ):
        if isinstance(source, list) or isinstance(source, tuple):
            source = chain.from_iterable(source)
        else:
            source = source
        qs = QuerySet(source)

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
            if 'addition_naming_info' not in kwargs \
                    or kwargs['addition_naming_info'] is None:
                kwargs['addition_naming_info'] = {}
                kwargs['addition_naming_info']['order'] = order
            result = self.queue.enqueue(
                self.pixie.download_illust,
                args=(),
                kwargs=kwargs,
            )
            with self._lock:
                record_obj.children.append((illust, result))


class _TaskRecord:
    def __init__(self, name):
        self.name = name
        self.result = None
        self.children = []
