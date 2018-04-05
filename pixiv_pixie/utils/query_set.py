from functools import partial, wraps
import itertools

SEP = '__'


class OperatorCollection:
    """Provide some binary operations."""

    default_operator = 'exact'

    @classmethod
    def _remove_case(cls, a, b):
        if isinstance(a, str):
            a = a.lower()
        if isinstance(b, str):
            b = b.lower()
        return a, b

    @classmethod
    def exact(cls, lhs, rhs):
        """Exact match.
        >>> operator = OperatorCollection
        >>> operator.exact(1, 2)
        False
        >>> operator.exact(1, '1')
        False
        >>> operator.exact(42, 42)
        True
        """
        return lhs == rhs

    eq = exact

    @classmethod
    def nexact(cls, lhs, rhs):
        """Not match.
        >>> operator = OperatorCollection
        >>> operator.nexact(1, 2)
        True
        >>> operator.nexact(1, '1')
        True
        >>> operator.nexact(42, 42)
        False
        """
        return lhs != rhs

    ne = nexact

    @classmethod
    def iexact(cls, lhs, rhs):
        """Case-insensitive exact match.
        >>> operator = OperatorCollection
        >>> operator.iexact('apple', 'Apple')
        True
        >>> operator.iexact('10', 10)
        False
        >>> operator.iexact('And', 'end')
        False
        """
        lhs, rhs = cls._remove_case(lhs, rhs)
        return cls.exact(lhs, rhs)

    @classmethod
    def contains(cls, lhs, rhs):
        """Case-sensitive containment test.
        >>> operator = OperatorCollection
        >>> operator.contains('boy meets girl', 'boy')
        True
        >>> operator.contains('Apple Inc.', 'apple')
        False
        >>> operator.contains({'ans': 42}, 'ans')
        True
        """
        return rhs in lhs

    @classmethod
    def icontains(cls, lhs, rhs):
        """Case-insensitive containment test.
        >>> operator = OperatorCollection
        >>> operator.icontains('Boy meets Girl', 'boy')
        True
        >>> operator.icontains('Apple Inc.', 'apple')
        True
        >>> operator.icontains({'ans': 42}, 'ANS')
        True
        """
        lhs, rhs = cls._remove_case(lhs, rhs)
        return cls.contains(lhs, rhs)

    @classmethod
    def belongs(cls, lhs, rhs):
        """Belonging test.
        >>> operator = OperatorCollection
        >>> operator.belongs('boy', ['boy', 'meets', 'girl'])
        True
        >>> operator.belongs(1, range(5))
        True
        >>> operator.belongs('ans', {'ans': 42})
        True
        >>> operator.belongs('another_ans', {'ans': 42})
        False
        """
        return lhs in rhs

    @classmethod
    def gt(cls, lhs, rhs):
        """Greater than."""
        return lhs > rhs

    @classmethod
    def gte(cls, lhs, rhs):
        """Greater than or equal to."""
        return lhs >= rhs

    @classmethod
    def lt(cls, lhs, rhs):
        """Less than."""
        return lhs < rhs

    @classmethod
    def lte(cls, lhs, rhs):
        """Less than or equal to."""
        return lhs <= rhs

    @classmethod
    def startswith(cls, lhs, rhs):
        """Case-sensitive starts-with."""
        return lhs.startswith(rhs)

    @classmethod
    def istartswith(cls, lhs, rhs):
        """Case-insensitive starts-with."""
        lhs, rhs = cls._remove_case(lhs, rhs)
        return cls.startswith(lhs, rhs)

    @classmethod
    def endswith(cls, lhs, rhs):
        """Case-sensitive ends-with."""
        return lhs.endswith(rhs)

    @classmethod
    def iendswith(cls, lhs, rhs):
        """Case-insensitive ends-with."""
        lhs, rhs = cls._remove_case(lhs, rhs)
        return cls.endswith(lhs, rhs)

    @classmethod
    def in_range(cls, lhs, rhs):
        """Range test (inclusive).
        >>> operator = OperatorCollection
        >>> operator.in_range(42, (35, 70))
        True
        >>> operator.in_range(1, (1, 1))
        True
        >>> operator.in_range('a', ('', 'b'))
        True
        """
        return rhs[0] <= lhs <= rhs[1]

    @classmethod
    def isnone(cls, lhs, rhs):
        """Takes either True or False, which correspond to Python expression of
        IS NONE and IS NOT NONE, respectively.
        """
        if rhs:
            return lhs is None
        else:
            return lhs is not None


def _get_attribute(obj, attribute_list):
    value = obj
    for attribute_name in attribute_list:
        attr = getattr(value, attribute_name)
        if callable(attr):
            value = attr()
        else:
            value = attr
    return value


def _attribute_lookup(
        obj, query_string, query_value, sep=SEP,
        operator_collection=OperatorCollection,
):
    """
    >>> from datetime import datetime
    >>> d = datetime(2000, 1, 23, 7, 59, 4)
    >>> _attribute_lookup(d, 'day', 23)
    True
    >>> _attribute_lookup(d, 'ctime__lower__exact', 'sun jan 23 07:59:04 2000')
    True
    """
    attribute_list = query_string.split(sep)
    if hasattr(operator_collection, attribute_list[-1]) \
            and callable(getattr(operator_collection, attribute_list[-1])):
        operator_name = attribute_list.pop()
    else:
        operator_name = operator_collection.default_operator
    operator = getattr(operator_collection, operator_name)

    value = _get_attribute(obj, attribute_list)

    return operator(value, query_value)


def attribute_lookup(obj, *_, **query):
    """Django-like field lookups.
    >>> from datetime import datetime
    >>> d = datetime(2000, 1, 23, 7, 59, 4)
    >>> attribute_lookup(d, day=23, second=4)
    True
    >>> attribute_lookup(d, year__lt=2017)
    True
    """
    for query_str, query_val in query.items():
        if not _attribute_lookup(
                obj, query_str, query_val,
                SEP, OperatorCollection,
        ):
            return False
    return True


class Q:
    """Query object. Used to build complex query.

    e.g. (Q(age__lt=18) & Q(paid=True)) | Q(is_admin=True)
    """

    def __init__(self, **query):
        self._query = query

    def validate(self, obj):
        return attribute_lookup(obj, **self._query)

    def __invert__(self):
        return QNot(self)

    def __and__(self, other):
        return QAnd(self, other)

    def __or__(self, other):
        return QOr(self, other)


class QNot(Q):
    def __init__(self, q):
        self._q = q
        super().__init__()

    def validate(self, obj):
        return not self._q.validate(obj)


class QAnd(Q):
    def __init__(self, lhs, rhs):
        self._lhs = lhs
        self._rhs = rhs
        super().__init__()

    def validate(self, obj):
        return self._lhs.validate(obj) and self._rhs.validate(obj)


class QOr(Q):
    def __init__(self, lhs, rhs):
        self._lhs = lhs
        self._rhs = rhs
        super().__init__()

    def validate(self, obj):
        return self._lhs.validate(obj) or self._rhs.validate(obj)


class QuerySet:
    """Django-like query set.
    """

    def __init__(self, data_source):
        self._data_source = data_source
        self._iter = iter(self._data_source)

    def __iter__(self):
        return self

    def __next__(self):
        return next(self._iter)

    def filter(self, q_object=None, **query):
        """Example:

        for illust in QuerySet(pixie.ranking()).filter(aspect_ratio__lt=1):
            pixie.download_illust(illust)

        Or more complex filter:

        for illust in QuerySet(pixie.ranking()).filter(
            Q(aspect_ratio__lt=1) | Q(tags__contains='オリジナル'),
        ):
            pixie.download_illust(illust)
        """

        def _filter(item):
            if q_object is None:
                return attribute_lookup(item, **query)
            else:
                return q_object.validate(item) \
                       and attribute_lookup(item, **query)

        return QuerySet(filter(_filter, self))

    def func_filter(self, func):
        """Warp of python built-in filter()."""
        return QuerySet(filter(func, self))

    def exclude(self, q_object=None, **query):
        """Similar to filter()."""

        def _filter(item):
            if q_object is None:
                return not attribute_lookup(item, **query)
            else:
                return not (q_object.validate(item)
                            and attribute_lookup(item, **query))

        return QuerySet(filter(_filter, self))

    def order_by(self, *fields):
        """Sort items before yield.

        Sort items before yield. Field name starts with '-' means reversed. It
        may take many times for it will fetch all items first.
        Example:

        for illust in QuerySet(pixie.search('オリジナル')) \
                .exclude(tags__contains='R-18') \
                .order_by('-total_bookmarks'):
            pixie.download_illust(illust)

        """
        if not fields:
            return self

        data = list(self)
        for field in reversed(fields):

            reverse = False
            if field.startswith('-'):
                reverse = True
                field = field[1:]

            data.sort(
                key=partial(_get_attribute, attribute_list=field.split(SEP)),
                reverse=reverse,
            )

        return QuerySet(data)

    def reversed(self):
        """Warp of python built-in reversed()."""
        return QuerySet(reversed(list(self)))

    def limit(self, max_num):
        """Only yield the first max_num items."""
        return QuerySet(itertools.islice(self, max_num))

    def enumerate(self, start=0):
        """Warp of python built-in enumerate()."""
        return enumerate(self, start=start)


def query_set(gen):
    """This is a convenience decorator to wrap generator to QuerySet."""

    @wraps(gen)
    def new_gen(*args, **kwargs):
        return QuerySet(gen(*args, **kwargs))

    return new_gen
