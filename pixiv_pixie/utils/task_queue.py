from datetime import datetime
from enum import Enum
from functools import partial
import logging
from queue import Queue, Empty
from threading import Condition, Lock, Thread

# logger
logger = logging.getLogger(__name__)


# exceptions
class Error(Exception):
    pass


class Timeout(Error):
    pass


# enum
class TaskStatus(Enum):
    PENDING = 'PENDING'
    STARTED = 'STARTED'
    FAILURE = 'FAILURE'
    SUCCESS = 'SUCCESS'


# classes
class TaskQueue:
    def __init__(self, worker_wait=0.2):
        """Initialize.

        Args:
            worker_wait: The period of which worker checks the halt flag.
        """
        self._worker_wait = worker_wait

        self._worker_lock = Lock()
        self._workers = []
        self._halt_flag = False

        self._queue = Queue()

    def spawn_workers(self, number):
        """Spawn workers.

        Spawn workers. Can only be called when there is no worker spawned.

        Args:
            number: Number of workers to be spawned.

        Raises:
            RuntimeError: If workers already been spawned..
        """
        with self._worker_lock:
            if self._workers:
                raise RuntimeError('Workers already been spawned.')
            self._halt_flag = False
            for _ in range(number):
                thread = Thread(target=self._worker)
                thread.start()
                self._workers.append(thread)

    def halt_workers(self):
        """Halt and remove all workers.

        This method will block the calling thread until all workers have
            stopped.
        """
        with self._worker_lock:
            self._halt_flag = True
            for worker in self._workers:
                worker.join()
            self._workers.clear()

    def enqueue(self, func, args, kwargs):
        """Add a task into queue and return a TaskResult object.

        Args:
            func: The task function.
            args: Positional argument that will be passed to func.
            kwargs: Keyword argument that will be passed to func.
        """
        task_result = TaskResult(queue=self)
        self._queue.put((func, args, kwargs, task_result))
        return task_result

    def task(self, *args, **kwargs):
        """Decorator to create a task class out of any callable."""
        if len(args) == 1:
            if callable(args[0]):
                return Task(*args, queue=self)
            else:
                raise TypeError('argument 1 to @task() must be a callable')
        elif args:
            raise TypeError(
                '@task() takes exactly 1 argument ({0} given)'.format(
                    sum([len(args), len(kwargs)])))
        else:
            return partial(Task, queue=self)  # TODO(xdynix): complex task

    def _worker(self):
        while not self._halt_flag:
            try:
                func, args, kwargs, task_result = self._queue.get(
                    timeout=self._worker_wait)
            except Empty:
                pass
            else:
                try:
                    try:
                        task_result._status = TaskStatus.STARTED
                        result = func(*args, **kwargs)
                    except Exception as e:
                        task_result._set_exception(e)
                        task_result._status = TaskStatus.FAILURE
                    else:
                        task_result._set_result(result)
                        task_result._status = TaskStatus.SUCCESS
                except Exception as e:
                    logger.error('Unhandled error in worker thread.')
                    logger.exception(e)
                finally:
                    self._queue.task_done()


class TaskResult:
    def __init__(self, queue):
        self._queue = queue

        self._lock = Lock()
        self._status = TaskStatus.PENDING
        self._result = None
        self._exception = None
        self._last_finish = None

        self._cv = Condition()

    @property
    def queue(self):
        """The TaskQueue object that it belongs to."""
        return self._queue

    @property
    def status(self):
        """The tasks status."""
        return self._status
    state = status

    @property
    def result(self):
        """Task return value."""
        with self._lock:
            return self._result

    @property
    def exception(self):
        """If the task raised an exception, this will be the exception instance,
         otherwise None."""
        with self._lock:
            return self._exception

    @property
    def last_finish(self):
        """The last time the task finished. Will be a datetime object or None.
        """
        with self._lock:
            return self._last_finish

    def ready(self):
        """Return True if the task has executed."""
        return bool(self.last_finish)

    def successful(self):
        """Return True if the task executed successfully."""
        return self.exception is None

    def failed(self):
        """Return True if the task failed."""
        return self.exception is not None

    def get(self, timeout=None, propagate=True):
        """Wait until task is ready, and return its result.

        Args:
            timeout: How long to wait, in seconds, before the operation times
                out.
            propagate: Re-raise exception if the task failed.
        """
        with self._cv:
            while not self.ready():
                been_notified = self._cv.wait(timeout)
                if not been_notified and timeout is not None:
                    raise Timeout
            if propagate and self._exception is not None:
                raise self._exception
            return self.result

    def _set_result(self, result):
        with self._cv:
            with self._lock:
                self._result = result
                self._exception = None
                self._last_finish = datetime.now()
            self._cv.notify()

    def _set_exception(self, exception):
        with self._cv:
            with self._lock:
                self._result = None
                self._exception = exception
                self._last_finish = datetime.now()
            self._cv.notify()


class Task:
    def __init__(self, func, queue, name=None):
        self._func = func
        self._queue = queue
        if name is None:
            self._name = func.__name__
        else:
            self._name = name

    @property
    def name(self):
        return self._name

    def __call__(self, *args, **kwargs):
        return self._func(*args, **kwargs)

    def delay(self, *args, **kwargs):
        return self._queue.enqueue(self._func, args, kwargs)
