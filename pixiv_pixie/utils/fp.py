# This file contains code (class `F` and `Stream`) modified from
# https://github.com/kachayev/fn.py
#
# Copyright 2013 Alexey Kachayev
# Modifications Copyright 2019 Xdynix
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Some functional programming utilities."""

# pylint: disable=too-many-lines

import operator
import random
import re
from collections import deque
from functools import partial, reduce
from itertools import (
    chain,
    count,
    cycle,
    filterfalse,
    islice,
    repeat,
    starmap,
    takewhile,
)
from sys import maxsize


def partial_right(func, *args, **kwargs):
    """Create right partial function.

    This function is like `functools.partial` except that partially applied
    positional arguments are appended to the positional arguments it receives.

    >>> partial_right(list.__add__, [1, 2, 3])([4, 5, 6])
    [4, 5, 6, 1, 2, 3]

    Args:
        func: The function that will be wrapped.
        args: The positional arguments that will be appended.
        kwargs: The keyword arguments that will be called with `func`.

    Returns:
        A callable object which behave like a partial object but with out any
        attribute.
    """

    def new_func(*f_args, **f_kwargs):
        new_args = chain(f_args, args)
        new_kwargs = kwargs.copy()
        new_kwargs.update(f_kwargs)
        return func(*new_args, **new_kwargs)

    return new_func


# pylint: disable=invalid-name
class F:
    """A simple functor.

    Provide simple functions composition and partial function syntax.
    Usage example:
    >>> from operator import add, mul
    >>> func = F() << (add, 2) << (mul, 5)
    >>> func(8)
    42
    >>> sum_and_print = F(sum).and_then(print)
    >>> sum_and_print(range(10))
    45
    >>> inc = F(add, 1)
    >>> inc(5)
    6
    """
    __slots__ = ('_func',)

    @classmethod
    def identity(cls):
        """Returns an identity function."""
        return cls(lambda x: x)

    # pylint: disable=keyword-arg-before-vararg
    def __init__(self, func=None, *args, **kwargs):
        if func is None:
            func = self.identity()
        if args or kwargs:
            func = partial(func, *args, **kwargs)
        self._func = func

    @property
    def func(self):
        """The raw callable object."""
        return self._func

    def __call__(self, *args, **kwargs):
        """Calls self as a function."""
        return self._func(*args, **kwargs)

    def copy(self):
        """Returns a copy of the `F` object."""
        return self.__class__(self.func)

    __copy__ = copy

    @classmethod
    def _convert_implicit_partial(cls, obj):
        """Simplify partial execution syntax by converting tuple and list into
        partial function."""
        if isinstance(obj, (tuple, list)):
            obj = cls(*obj)
        return obj

    def compose(self, before):
        """Returns a composed function that first applies the `before`
        function to its input, and then applies this function to the result.

        Args:
            before: The function to apply before this function is applied.
        """
        before = self._convert_implicit_partial(before)
        return self.__class__(
            lambda *args, **kwargs:
            self(before(*args, **kwargs))
        )

    __lshift__ = compose
    __rrshift__ = compose

    def and_then(self, after):
        """Returns a composed function that first applies this function to its
        input, and then applies the `after` function to the result.

        Args:
            after: The function to apply after this function is applied.
        """
        after = self._convert_implicit_partial(after)
        return self.__class__(
            lambda *args, **kwargs:
            after(self(*args, **kwargs))
        )

    __rshift__ = and_then
    __rlshift__ = and_then


def _xor(lhs, rhs):
    """Shorthand of logical XOR expression."""
    return bool(lhs) != bool(rhs)


# pylint: disable=invalid-name
class Q(F):
    """A functor that usually used as a predicate.

    This functor is expected to use as a predicate. That is, only accepts one
    argument and return a Boolean value.

    The difference between this class and its base class `F` is the difference
    in the initialization and the more composite methods.

    When initializing, you can pass in a callable object. But additional
    positional arguments are not allowed. And the keyword arguments will be
    treated as field lookup expressions. When both callable object and field
    lookup expressions are received, they are considered to be "AND"ed
    together.

    The syntax for field lookup expressions is basically the same as for
    Django. Which is a series of keyword arguments in the form:
        field__lookup_name=param
    Each keyword argument is treated as a test. And all these tests are
    "AND"ed together.

    The `field` part is a number of attribute names or subscript names that
    are concatenated with __ (double underscore). A name will first be tried
    as the attribute name and then try to be the subscript name. If the name
    is the name of a method, it will be called without passing any arguments.
    For example, `name__lower` might first get the name attribute and called
    `str.lower()` on it.

    The `lookup_name` and `param` parts are used to test the value obtained in
    the `field` part. Built-in lookups are listed below.

        "eq", "exact":
            Equality test. Equivalent to `field == param`.
        "ne", "neq":
            Inequality test. Equivalent to `field != param`.
        "is":
            Same-object test. Equivalent to `field is param`.
        "is_not":
            Different-object test. Equivalent to `field is not param`.
        "contains":
            Containment test. Equivalent to `param in field`.
        "in":
            Reverse containment test. Equivalent to `field in param`.
        "lt":
            Less than. Equivalent to `field < param`.
        "le", "lte":
            Less than or equal to. Equivalent to `field <= param`.
        "gt":
            Greater than. Equivalent to `field > param`.
        "ge", "gte":
            Greater than or equal to. Equivalent to `field >= param`.
        "divisible_by":
            Divisibility test. Equivalent to `field % param == 0`.
        "range", "inrange", "in_range":
            Range test (inclusive). `Q(score__range=(0, 100))` is equivalent
            to `Q(lambda x: 0 <= x.score <= 100)`.
        "isnull", "is_null":
            Takes either `True` or `False`, which correspond to
            `field is None` and `field is not None`, respectively.
        "startswith":
            String starts-with test. Equivalent to
            `str.startswith(field, param)`.
        "endswith":
            String ends-with test. Equivalent to
            `str.endswith(field, param)`.
        "regex":
            Case-sensitive regular expression match.
            `Q(title__regex=r'^(An?|The) +')` is equivalent to
            `Q(lambda x: re.fullmatch(r'^(An?|The) +', x.title) is not None)`.
        "iregex":
            Case-insensitive regular expression match. Similar to "regex" but
            will use IGNORECASE flag.
        "isinstance":
            Type instance test. Equivalent to `isinstance(field, param)`.
        "issubclass":
            Subclass test. Equivalent to `issubclass(field, param)`.

    For convenience, if no lookup name provided, it is treated as "eq". It is
    also possible to register custom lookups by calling `Q.register_lookup`.

    `Q` objects can be combined using the &, | and ^ operators. When an
    operator is used on two `Q` objects, it yields a new `Q` object. Q objects
    can be negated using the ~ operator. With these operators you can build
    complex lookups.

    Usage example:
    >>> from datetime import datetime, time
    >>> d = datetime(year=2012, month=12, day=21)
    >>> is_even_day_date = Q(day__divisible_by=2)
    >>> is_even_day_date(d)
    False
    >>> is_midnight = Q(time=time(hour=0, minute=0, second=0))
    >>> is_midnight(d)
    True
    >>> q = Q(day__gt=25) | ~Q(year=2012)
    >>> q(d)
    False
    """
    SEP = '__'  # Lookup expression separator.
    _lookups = {}  # Registered lookups.
    _default_lookup_name = 'eq'  # Default lookup if no name provided.

    @classmethod
    def register_lookup(cls, lookup_name, lookup_func=None):
        """Registers custom lookup.

        Use this function to register custom lookups. A custom lookup should
        be a function that accepts two arguments and return a Boolean value.
        Where the first argument is the value obtained by `field` part of
        lookup expression, and the second argument is the `param` part.

        When you register a custom lookup with the name of a built-in lookup,
        the built-in one will be shadowed and cannot be recovered.

        Args:
            lookup_name: The lookup name. Can be any string that does not
                contain "__".
            lookup_func: The custom lookup function.

        Returns:
            If both `lookup_name` and `lookup_func` are provided, it will
            return the lookup function itself. If only `lookup_name` is
            provided, it will return a decorator that registers the decorated
            function.

        Raises:
            ValueError: The `lookup_name` is invalid (contains "__").
        """
        lookup_name = str(lookup_name)
        sep = cls.SEP
        if sep in lookup_name:
            raise ValueError('Lookup name must not contain {!r}.'.format(sep))

        if lookup_func is not None:
            cls._lookups[lookup_name] = lookup_func
            return lookup_func

        return partial(cls.register_lookup, lookup_name)

    @classmethod
    def get_lookup(cls, lookup_name):
        """Fetched registered lookup function by name.

        Args:
            lookup_name: The registered name of lookup.

        Returns:
            The lookup function.

        Raises:
            ValueError: If the name is not registered.
        """
        if lookup_name not in cls._lookups:
            raise ValueError('Unknown lookup: {!r}.'.format(lookup_name))
        return cls._lookups[lookup_name]

    @classmethod
    def field_getter(cls, name):
        """Return a callable object that fetches field from its operand.

        Return a callable object that fetches `name` field from its operand.
        It will first try getting the operand's attribute which name is
        `name`. If the operand has a method which name is `name`, it will be
        called with no argument.

        When the operand has neither attribute nor method which name is
        `name`, the callable object will call the operand's __getitem__()
        method with `name` as argument.

        If the above attempts fail, the callable object will raises
        `LookupError`.

        Args:
            name: Field name.
        """

        if not name:
            return cls.identity()

        def f(obj):
            if hasattr(obj, name):
                value = getattr(obj, name)
                if callable(value):
                    value = value()
                return value
            try:
                return obj[name]
            except (TypeError, LookupError, ValueError):
                raise LookupError('{!r} has no field named {!r}.'.format(obj, name))

        return F(f)

    @classmethod
    def chained_field_getter(cls, *names):
        """Return a callable object that concatenated multiple field getters.

        Usage example:
        >>> person = {'name': {'first': 'John', 'last': 'Smith'}, 'age': 36}
        >>> first_name = Q.chained_field_getter('name', 'first')
        >>> first_name(person)
        'John'

        Args:
            *names: Field names.
        """
        return F(reduce(
            F.and_then,
            map(cls.field_getter, names),
            F.identity(),
        ))

    @classmethod
    def from_lookup(cls, lookup, param):
        """Build a `Q` object from a lookup expression.

        Usage example:
        >>> person = {'age': 16}
        >>> is_adult = Q.from_lookup('age__gte', 18)
        >>> is_adult(person)
        False

        Args:
            lookup: A string in the form "field__lookup_name"
            param: The `param` part of lookup expression.

        Returns:
            A `Q` object.
        """
        fields = lookup.split(cls.SEP)

        lookup_name = cls._default_lookup_name
        if fields[-1] in cls._lookups:
            lookup_name = fields.pop()

        get_field = cls.chained_field_getter(*fields)
        lookup_func = cls.get_lookup(lookup_name)

        return cls(
            lambda x:
            lookup_func(get_field(x), param)
        )

    def __init__(self, func=None, **kwargs):
        if kwargs:
            func = reduce(
                operator.and_,
                starmap(
                    self.from_lookup,
                    kwargs.items(),
                ),
                self.__class__(func),
            )
        super().__init__(func)

    def __invert__(self):
        """Return a new `Q` object that negate this `Q` object's result."""
        return self.__class__(
            lambda *args, **kwargs:
            not self(*args, **kwargs)
        )

    def __and__(self, other):
        """Return a new `Q` object that combines the results of this `Q`
        object and `other` by AND operator."""
        return self.__class__(
            lambda *args, **kwargs:
            self(*args, **kwargs) and other(*args, **kwargs)
        )

    def __rand__(self, other):
        """Return a new `Q` object that combines the results of `other` and
        this `Q` object by AND operator."""
        return self.__class__(
            lambda *args, **kwargs:
            other(*args, **kwargs) and self(*args, **kwargs)
        )

    def __or__(self, other):
        """Return a new `Q` object that combines the results of this `Q`
        object and `other` by OR operator."""
        return self.__class__(
            lambda *args, **kwargs:
            self(*args, **kwargs) or other(*args, **kwargs)
        )

    def __ror__(self, other):
        """Return a new `Q` object that combines the results of `other` and
        this `Q` object by OR operator."""
        return self.__class__(
            lambda *args, **kwargs:
            other(*args, **kwargs) or self(*args, **kwargs)
        )

    def __xor__(self, other):
        """Return a new `Q` object that combines the results of this `Q`
        object and `other` by XOR operator."""
        return self.__class__(
            lambda *args, **kwargs:
            _xor(self(*args, **kwargs), other(*args, **kwargs))
        )

    def __rxor__(self, other):
        """Return a new `Q` object that combines the results of `other` and
        this `Q` object by XOR operator."""
        return self.__class__(
            lambda *args, **kwargs:
            _xor(other(*args, **kwargs), self(*args, **kwargs))
        )


Q.register_lookup('eq', operator.eq)
Q.register_lookup('exact', operator.eq)
Q.register_lookup('ne', operator.ne)
Q.register_lookup('neq', operator.ne)
Q.register_lookup('is', operator.is_)
Q.register_lookup('is_not', operator.is_not)

Q.register_lookup('contains', operator.contains)
Q.register_lookup('in', lambda a, b: a in b)

Q.register_lookup('lt', operator.lt)
Q.register_lookup('le', operator.le)
Q.register_lookup('lte', operator.le)
Q.register_lookup('gt', operator.gt)
Q.register_lookup('ge', operator.ge)
Q.register_lookup('gte', operator.ge)
Q.register_lookup('divisible_by', lambda a, b: a % b == 0)


@Q.register_lookup('range')
@Q.register_lookup('inrange')
@Q.register_lookup('in_range')
def _in_range(x, r):
    low, high = r
    return low <= x <= high


@Q.register_lookup('isnull')
@Q.register_lookup('is_null')
def _is_null(a, b):
    return (a is None) == bool(b)


Q.register_lookup('startswith', str.startswith)
Q.register_lookup('endswith', str.endswith)
Q.register_lookup(
    'regex',
    lambda a, b:
    re.fullmatch(b, a) is not None,
)
Q.register_lookup(
    'iregex',
    lambda a, b:
    re.fullmatch(b, a, flags=re.IGNORECASE) is not None,
)

Q.register_lookup('isinstance', isinstance)
Q.register_lookup('issubclass', issubclass)


def _make_q(*args, **kwargs):
    """Make `Q` object from predicates and lookup expressions."""
    query = Q(lambda x: True)
    if args:
        query = reduce(
            operator.and_,
            map(Q, args),
            query
        )
    if kwargs:
        query = query & Q(**kwargs)
    return query


class Pipeline:  # Make Iterator Great Again! -- By Szcnorya
    # noinspection PyUnresolvedReferences
    """A combination of an iterable object and transformation function on it.

    A `Pipeline` object can be treated as a combination of an iterable object
    and a transformation function. This transformation function will takes an
    iterable object and perform some transformations, such as map and/or
    filter on it, then output the new iterable object.

    So the creation of `Pipeline` is very straightforward to pass an iterable
    object and a transformation function. Traversing a `Pipeline` object is
    equivalent to traversing the iterable object transformed by the function.

    >>> p = Pipeline([1, 2, 3, 4], lambda x: map(str, x))
    >>> list(p)
    ['1', '2', '3', '4']

    You must be aware that if the iterable object you pass in is a generator,
    you should also treat the `Pipeline` object as a generator: it can only be
    used once.

    You cannot switch the iterable objects and transformation functions of a
    `Pipeline` object. But when calling `copy()` method you can assign new
    values via keyword arguments.

    >>> p = Pipeline([1, 2, 3, 4], lambda x: map(str, x))
    >>> p2 = p.copy(source=[5, 6, 7, 8])
    >>> list(p2)
    ['5', '6', '7', '8']

    `Pipeline` class provides two methods `filter` and `map` to help you
    construct the transformation function. They work almost exactly the same
    way as the built-in `filter` and `map`, except that they only take effect
    when the transform function is called (that is, when traversing).

    >>> p = Pipeline(range(10)).filter(lambda x: x % 2 == 0).map(str)
    >>> list(p)
    ['0', '2', '4', '6', '8']

    These two functions return a new `Pipeline` object, using the same
    iterable object and the new transform function. So it is safe to keep and
    reuse old `Pipeline` objects.
    """
    __slots__ = ('_source', '_func')

    def __init__(self, source=(), func=F.identity()):
        self._source = source
        self._func = F(func)

    @property
    def source(self):
        """The iterable object."""
        return self._source

    @property
    def func(self):
        """The transformation function."""
        return self._func

    def __iter__(self):
        yield from self.func(self.source)

    def copy(self, *, source=None, func=None):
        """Shorthand method of creating a new `Pipeline` object using the
        same/new iterable object and transformation function.

        New value for the iterable object and transformation function must be
        passed by keyword arguments. If not provided, the default is the same
        as this object. All positional arguments are ignored.

        Args:
            source: The new iterable object. If `None`, keep the current one.
            func: The new transformation function. If `None`, keep the current
                one.

        Returns:
            A new `Pipeline` object.
        """
        if source is None:
            source = self.source
        if func is None:
            func = self.func
        return self.__class__(source, func)

    __copy__ = copy

    def compose(self, before):
        """Compose another transformation function before applying current one.

        Args:
            before: A transformation function that will be applied before
                current one.

        Returns:
            A new `Pipeline` object with the new transformation function.
        """
        return self.copy(func=self.func.compose(before))

    def and_then(self, after):
        """Compose another transformation function after applying current one.

        Args:
            after: A transformation function that will be applied after
                current one.

        Returns:
            A new `Pipeline` object with the new transformation function.
        """
        return self.copy(func=self.func.and_then(after))

    # pylint: disable=keyword-arg-before-vararg
    def filter(self, func):
        # noinspection PyUnresolvedReferences
        """Shorthand method for applying filtering transformation.

        This method creates a new `Pipeline` object that will apply the
        current transformation and then filter it.

        Usage example:
        >>> p = Pipeline(range(10)).filter(lambda x: x > 5)
        >>> list(p)
        [6, 7, 8, 9]

        Args:
            func: The prediction function used for filtering. Similar to
                the one for built-in `filter`.

        Returns:
            A new `Pipeline` object with the new transformation function.
        """
        query = _make_q(func)
        return self.and_then(partial(filter, query))

    def map(self, func):
        # noinspection PyUnresolvedReferences
        """Shorthand method for applying mapping transformation.

        This method creates a new `Pipeline` object that will apply the
        current transformation and then map it.

        Usage example:
        >>> p = Pipeline([1, 2, 3, 4]).map(lambda n: '-' * n)
        >>> list(p)
        ['-', '--', '---', '----']

        Args:
            func: The mapping function used for filtering. Similar to the
                one for built-in `map`.

        Returns:
            A new `Pipeline` object with the new transformation function.
        """
        return self.and_then(partial(map, F(func)))


class Query(Pipeline):
    """A `Pipeline` subclass with some convenient methods.

    This class is subclass of `Pipeline` and provides some easier to use
    methods. It is inspired by Django's `QuerySet` and implements many similar
    syntax.

    The keyword arguments of the `filter()` and `exclude()` methods are used
    to create a `Q` objects for filtering. So they are Django flavored:

    >>> records = [{'age': 19}, {'age': 20}, {'age': 18}, {'age': 16}]
    >>> q = Query(records).filter(age__gte=18).exclude(age__gte=20)
    >>> list(q)
    [{'age': 19}, {'age': 18}]
    >>> q = Query(records).filter(Q(age__gte=18) & ~Q(age__gte=20))
    >>> list(q)
    [{'age': 19}, {'age': 18}]

    There are three methods for changing the order of elements, `sort()`,
    `sort_by()`, and `reverse()`. Note that they will try to get all the
    elements first, then sort. This may use a lot of resources.
    """
    RANDOM_SORT = '?'  # Random sort identifier.

    # pylint: disable=arguments-differ
    def filter(self, *args, **kwargs):
        """Similar to `Pipeline.filter()`, except for the keyword arguments
        that will be used to build the `Q` object. See base class and `Q`
        class for detail.

        Returns:
            A new `Query` object with the new transformation function.
        """
        query = _make_q(*args, **kwargs)
        return self.and_then(partial(filter, query))

    def exclude(self, *args, **kwargs):
        """Similar to `filter()`, except that the elements that pass
        the test are excluded rather than retained.

        Returns:
            A new `Query` object with the new transformation function.
        """
        query = _make_q(*args, **kwargs)
        return self.and_then(partial(filterfalse, query))

    def sort(self, *, key=None, reverse=False):
        """Shorthand method for applying sorting transformation.

        Args:
            key: The key function. Similar to the one for built-in `sorted`.
            reverse: Reverse flag. Set to request the result in descending
                order.

        Returns:
            A new `Query` object with the new transformation function.
        """
        return self.and_then(partial(sorted, key=key, reverse=reverse))

    def sort_by(self, *fields):
        """Django flavored sorting.

        By calling `Query(data).sort_by('-name', 'birthday')`, the result will
        be ordered by field `name` descending, then by field `birthday`
        ascending. The value of a field is obtained by `Q.field_getter()`. The
        negative sign in front of "-name" indicates descending order.
        Ascending order is implied. To order randomly, use "?", like
        `Query(data).sort_by('?')`.

        It's possible to use field name like `birthday__month`, just like
        those for lookup expressions.

        If a value other than a string appears in the argument, it is treated
        as a key function for sorting:
        `Query(data).sort_by('name', lambda r: len(r.tags))`.

        Returns:
            A new `Query` object with the new transformation function.
        """
        try:
            fields = fields[:fields.index(self.RANDOM_SORT)]
        except ValueError:
            query = self
        else:
            def shuffle(iterable):
                iterable = tuple(iterable)
                yield from random.sample(iterable, k=len(iterable))

            query = self.and_then(shuffle)

        for arg in reversed(fields):
            if isinstance(arg, str):
                reverse = False
                if arg.startswith('-'):
                    reverse = True
                    arg = arg[1:]
                key = Q.chained_field_getter(*arg.split(Q.SEP))
                query = query.sort(key=key, reverse=reverse)
            else:
                query = query.sort(key=arg)

        return query

    def reverse(self):
        """Shorthand method for applying reversing transformation.

        Returns:
            A new `Query` object with the new transformation function.
        """
        return self.and_then(tuple).and_then(reversed)

    def distinct(self, *, key=None):
        """Shorthand method for applying distinct transformation.

        Apply the distinct transformation. Duplicate elements will be
        eliminated. Note that the set is used for this purpose. So you need to
        ensure that the element type is hashable.

        Returns:
            A new `Query` object with the new transformation function.
        """

        def unique(iterable):
            seen = set()
            seen_add = seen.add
            if key is None:
                for item in filterfalse(seen.__contains__, iterable):
                    seen_add(item)
                    yield item
            else:
                for item in iterable:
                    k = key(item)
                    if k not in seen:
                        seen_add(k)
                        yield item

        return self.and_then(unique)

    def prepend(self, *iterables):
        """Pending elements at the beginning of the iterable object.

        Usage example:
        >>> q = Query([1, 2, 3, 4]).prepend([5, 6, 7, 8], [9, 10])
        >>> list(q)
        [5, 6, 7, 8, 9, 10, 1, 2, 3, 4]

        Args:
            iterables: Iterable objects that will be prepended.

        Returns:
            A new `Query` object with the new transformation function.
        """
        return self.and_then(partial(chain, *iterables))

    def append(self, *iterables):
        """Pending elements at the ending of the iterable object.

        Usage example:
        >>> q = Query([1, 2, 3, 4]).append([5, 6, 7, 8], [9, 10])
        >>> list(q)
        [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

        Args:
            iterables: Iterable objects that will be appended.

        Returns:
            A new `Query` object with the new transformation function.
        """
        return self.and_then(partial_right(chain, *iterables))

    def slice(self, *args):
        """Shorthand method for applying slicing transformation.

        This method just applies `itertools.islice()` directly. See
        `itertools.islice()` for detail.

        Usage example:
        >>> q = Query(range(10)).slice(2, 8, 2)
        >>> list(q)
        [2, 4, 6]

        Args:
            args: Arguments that will be passed to `itertools.islice()`.

        Returns:
            A new `Query` object with the new transformation function.
        """
        return self.and_then(partial_right(islice, *args))

    def __getitem__(self, item):
        """Naive implementation for `__getitem__`.

        If the index is an integer, it will try to put all the elements into a
        tuple and applies `__getitem__` on it.

        If the index is a slicing, it will be passed to `Query.slice()`.

        Returns:
            A new `Query` object with the new transformation function.

        Raises:
            TypeError: If the indices type is other than `int` and `slice`.
        """
        if isinstance(item, int):
            return tuple(self)[item]
        if isinstance(item, slice):
            return self.slice(item.start, item.stop, item.step)
        raise TypeError('Unknown indices type: {!r}.'.format(type(item).__name__))

    def head(self, n):
        """Takes the first n elements."""
        return self[:n]

    def tail(self, n):
        """Takes the last n elements."""
        return self.and_then(partial(deque, maxlen=n))

    def repeat(self, times=2):
        """Repeatedly traversing all elements.

        If times=None, it will repeat infinitely.

        If times less than or equal to one, it will not repeat and all
        elements will be traversed once.

        Otherwise it will traverse through all the elements as many times.

        Returns:
            A new `Query` object with the new transformation function.
        """
        if times is None:
            return self.and_then(cycle)
        if times > 1:
            return self.and_then(
                partial_right(repeat, times)
            ).and_then(
                chain.from_iterable
            )
        return self.copy()


class Stream:
    """Lazy-evaluated element sequence.

    You can iterate over several iterable objects through a `Stream` object.
    The elements are lazy-evaluated from those iterable objects and are stored
    for later use. New elements can be appended by using `<<` operator.

    Usage example:
    >>> s = Stream() << [1, 2, 3, 4, 5]
    >>> list(s)
    [1, 2, 3, 4, 5]
    >>> s[3]
    4
    >>> list(s[1::2])
    [2, 4]
    >>> s = Stream() << range(6) << [6, 7]
    >>> list(s)
    [0, 1, 2, 3, 4, 5, 6, 7]

    `Stream` can be used to create infinite sequences. You can calculate a
    Fibonacci sequence like this:
    >>> from operator import add
    >>> fib = Stream()
    >>> fib = fib << [0, 1] << map(add, fib, fib[1:])
    >>> list(fib[:10])
    [0, 1, 1, 2, 3, 5, 8, 13, 21, 34]
    >>> fib[20]
    6765
    >>> list(fib[30:35])
    [832040, 1346269, 2178309, 3524578, 5702887]
    >>> list(fib[34:29:-1])
    [5702887, 3524578, 2178309, 1346269, 832040]
    """
    __slots__ = ('_source', '_buffer')

    def __init__(self, source=()):
        self._source = iter(source)
        self._buffer = []

    def __lshift__(self, other):
        """Append new elements at the end.

        Returns:
            The `Stream` object itself.
        """
        self._source = chain(self._source, other)
        return self

    def __getitem__(self, item):
        """Subscript operation.

        Note that if you use a negative step and you don't specify a start
        index, the `Stream` object will try to evaluate all the elements,
        which can be very expensive.

        Returns:
            If the indices is an integer, it will try to access that element
            and return. If the indices is a slice, it will returns a new
            `Stream` object to traverse this slicing.

        Raises:
            ValueError: The indices is a negative integer.
            IndexError: Indices out of range.
        """
        if isinstance(item, int):
            if item < 0:
                raise ValueError('Negative indices are not allowed.')
            self._fill_buffer_to(item + 1)
            return self._buffer[item]
        if isinstance(item, slice):
            def slicer():
                start, stop, step = item.indices(maxsize)
                if step > 0:
                    yield from map(self.__getitem__, takewhile(
                        lambda i: self._fill_buffer_to(i + 1),
                        range(start, stop, step),
                    ))
                elif step < 0:
                    self._fill_buffer_to(start + 1)
                    start = min(start, len(self._buffer) - 1)
                    yield from map(
                        self.__getitem__,
                        range(start, stop, step),
                    )

            return self.__class__() << slicer()
        raise TypeError('Unknown indices type: {!r}.'.format(type(item).__name__))

    def __iter__(self):
        """Stream iteration."""
        for idx in count():
            if idx >= len(self._buffer):
                fill_result = self._fill_buffer_to(idx + 1)
                if not fill_result:
                    return
            yield self[idx]

    def _fill_buffer_to(self, size):
        """Evaluate elements from iterable objects and store them.

        Try filling the buffer with the evaluated elements until it reaches
        the size.

        Returns:
            `True` if the required size is reached, otherwise `False`.
        """
        while len(self._buffer) < size:
            try:
                item = next(self._source)
            except StopIteration:
                return False
            else:
                self._buffer.append(item)
        return True


__all__ = (
    'partial',
    'partial_right',
    'F', 'Q',
    'Pipeline',
    'Query',
    'Stream',
)
