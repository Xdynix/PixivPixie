"""Unittest for `pixiv_pixie.utils.fp`."""

# pylint: disable=bad-continuation, invalid-name

import unittest
from collections import namedtuple
from datetime import date
from doctest import DocTestSuite
from itertools import chain
from operator import add, mul

from pixiv_pixie.utils import fp
from pixiv_pixie.utils.fp import partial_right, F, Q, Pipeline, Query, Stream


def load_tests(_, tests, __):
    """Load doctests."""
    tests.addTests(DocTestSuite(fp))
    return tests


class TestPartialRight(unittest.TestCase):
    """Tests for `partial_right`."""

    def test_positional_arguments(self):
        """Test `partial_right` with positional arguments."""

        add_123 = partial_right(list.__add__, [1, 2, 3])
        self.assertEqual(
            add_123([4, 5, 6]),
            [4, 5, 6, 1, 2, 3],
        )

        list_456 = partial_right(lambda *args: list(args), 4, 5, 6)
        self.assertEqual(
            list_456(1, 2, 3),
            [1, 2, 3, 4, 5, 6],
        )

    def test_keyword_arguments(self):
        """Test `partial_right` with keyword arguments."""

        dict_with_answer = partial_right(dict, answer=42)
        self.assertEqual(
            dict_with_answer(when='now'),
            {'when': 'now', 'answer': 42},
        )
        self.assertEqual(
            dict_with_answer(answer=0),
            {'answer': 0},
        )


class TestF(unittest.TestCase):
    """Test for `F`."""

    def test_identity(self):
        """Test `F.identity`."""
        func = F.identity()
        obj = object()
        self.assertIsInstance(func, F)
        self.assertIs(func(obj), obj)

    def test_init_without_argument(self):
        """Test `F.__init__` without argument."""
        func = F()
        obj = object()
        self.assertIs(func(obj), obj)

    def test_init_with_arguments(self):
        """Test `F.__init__` with positional argument and keyword argument."""
        func = F(sum)
        a_range = range(10)
        self.assertEqual(func(a_range), sum(a_range))

        func = F(add, 3)
        self.assertEqual(func(5), 8)

        func = F(int, base=2)
        self.assertEqual(func('1001'), 9)

    def test_func(self):
        """Test `F.func`."""
        func = F(sum)
        self.assertIs(func.func, sum)

    def test_copy(self):
        """Test `F.copy`."""
        func = F(sum)
        self.assertIs(func.copy().func, func.func)
        self.assertIsNot(func.copy(), func)

    def test_compose(self):
        """Test `F.compose`."""

        func = F().compose(F(add, 2)).compose(F(mul, 5))
        self.assertEqual(func(8), 42)

        func = F() << (add, 2) << (mul, 5)
        self.assertEqual(func(8), 42)

        func = (mul, 5) >> F() >> (add, 2)
        self.assertEqual(func(8), 42)

    def test_and_then(self):
        """Test `F.and_then`."""
        func = F().and_then(F(mul, 5)).and_then(F(add, 2))
        self.assertEqual(func(8), 42)

        func = F() >> (mul, 5) >> (add, 2)
        self.assertEqual(func(8), 42)

        func = (add, 2) << F() << (mul, 5)
        self.assertEqual(func(8), 42)

    def test_complicate_composing(self):
        """Test complicate composing."""
        func = (add, 2) >> F() << (mul, 5)
        self.assertEqual(func(8), 42)


# pylint: disable=too-many-public-methods
class TestQ(unittest.TestCase):
    """Test for `Q`."""

    def setUp(self):
        Record = namedtuple(
            'Record',
            ['name', 'score', 'birthday', 'weapon'],
            defaults=[None],
        )

        # noinspection PyArgumentList
        self.record_1 = Record('John Smith', 85, date(1990, 3, 17))
        self.record_2 = Record('Jimmy Wang', 97, date(1989, 12, 29), weapon='Sword')
        self.dict_data = {
            'name': {
                'first': 'Foo',
                'last': 'Bar',
            },
            'tags': [
                'Human',
                'Alive',
            ],
            'is_active': True,
            'cls': Record,
        }
        self.table = {
            '00': {'a': 0, 'b': 0},
            '01': {'a': 0, 'b': 1},
            '10': {'a': 1, 'b': 0},
            '11': {'a': 1, 'b': 1},
        }

    def test_register_lookup_by_calling(self):
        """Test `Q.register_lookup` by directly calling it."""
        with self.assertRaises(ValueError):
            Q.get_lookup('is_good')

        def is_good(birthday, param):
            if param:
                return birthday.month == 3
            return birthday.month == 12

        Q.register_lookup('is_good', is_good)
        with self.assertRaises(ValueError):
            Q.register_lookup('__is_good')
        with self.assertRaises(ValueError):
            Q.register_lookup('is__good')
        with self.assertRaises(ValueError):
            Q.register_lookup('is_good__')

        has_good_birthday = Q(birthday__is_good=True)
        has_bad_birthday = Q(birthday__is_good=False)

        self.assertTrue(has_good_birthday(self.record_1))
        self.assertTrue(has_bad_birthday(self.record_2))

    def test_register_lookup_by_decorator(self):
        """Test `Q.register_lookup` by use it as decorator."""
        with self.assertRaises(ValueError):
            Q.get_lookup('longer_than')

        @Q.register_lookup('longer_than')
        # pylint: disable=unused-variable
        def longer_than(value, param):
            return len(value) > param

        more_than_3_tags = Q(tags__longer_than=3)
        self.assertFalse(more_than_3_tags(self.dict_data))

    def test_get_lookup(self):
        """Test `Q.get_lookup`."""
        with self.assertRaises(ValueError):
            Q.get_lookup('foobar')
        equal = Q.get_lookup('eq')
        self.assertTrue(equal(42, 42))

    def test_field_getter(self):
        """Test `Q.field_getter`."""
        get_name = Q.field_getter('name')
        self.assertEqual(get_name(self.record_1), 'John Smith')
        self.assertEqual(
            get_name(self.dict_data),
            {'first': 'Foo', 'last': 'Bar'},
        )

        get_lower = Q.field_getter('lower')
        self.assertEqual(get_lower(self.record_1.name), 'john smith')

        q = Q.field_getter('')
        self.assertIs(q(self.record_1), self.record_1)

        with self.assertRaises(LookupError):
            get_lower(self.record_1)

    def test_chained_field_getter(self):
        """Test `Q.chained_field_getter`."""
        get_upper_name = Q.chained_field_getter('name', 'upper')
        self.assertEqual(get_upper_name(self.record_2), 'JIMMY WANG')
        get_year_of_birth = Q.chained_field_getter('birthday', 'year')
        self.assertEqual(get_year_of_birth(self.record_2), 1989)

    def test_from_lookup(self):
        """Test `Q.from_lookup`."""
        is_90s = Q(birthday__year__in_range=(1990, 1999))
        self.assertTrue(is_90s(self.record_1))
        self.assertFalse(is_90s(self.record_2))

    def test_init_with_callable(self):
        """Test `Q.__init__` with a callable argument."""
        has_weapon = Q(lambda r: r.weapon is not None)
        self.assertFalse(has_weapon(self.record_1))
        self.assertTrue(has_weapon(self.record_2))

    def test_init_with_lookup_expression(self):
        """Test `Q.__init__` with lookup expression."""
        is_90s = Q(birthday__year__in_range=(1990, 1999))
        self.assertTrue(is_90s(self.record_1))
        self.assertFalse(is_90s(self.record_2))

    def test_invert(self):
        """Test `Q.__invert__`."""
        q = ~Q(a=1)
        self.assertTrue(q(self.table['00']))
        self.assertFalse(q(self.table['10']))

    def test_and(self):
        """Test `Q.__and__`."""
        q = Q(a=1) & Q(b=1)
        self.assertFalse(q(self.table['00']))
        self.assertFalse(q(self.table['01']))
        self.assertFalse(q(self.table['10']))
        self.assertTrue(q(self.table['11']))

    def test_rand(self):
        """Test `Q.__rand__`."""
        q = (lambda t: t['a'] == 1) & Q(b=1)
        self.assertFalse(q(self.table['00']))
        self.assertFalse(q(self.table['01']))
        self.assertFalse(q(self.table['10']))
        self.assertTrue(q(self.table['11']))

    def test_or(self):
        """Test `Q.__or__`."""
        q = Q(a=1) | Q(b=1)
        self.assertFalse(q(self.table['00']))
        self.assertTrue(q(self.table['01']))
        self.assertTrue(q(self.table['10']))
        self.assertTrue(q(self.table['11']))

    def test_ror(self):
        """Test `Q.__ror__`."""
        q = (lambda t: t['a'] == 1) | Q(b=1)
        self.assertFalse(q(self.table['00']))
        self.assertTrue(q(self.table['01']))
        self.assertTrue(q(self.table['10']))
        self.assertTrue(q(self.table['11']))

    def test_xor(self):
        """Test `Q.__xor__`."""
        q = Q(a=1) ^ Q(b=1)
        self.assertFalse(q(self.table['00']))
        self.assertTrue(q(self.table['01']))
        self.assertTrue(q(self.table['10']))
        self.assertFalse(q(self.table['11']))

    def test_rxor(self):
        """Test `Q.__rxor__`."""
        q = (lambda t: t['a'] == 1) ^ Q(b=1)
        self.assertFalse(q(self.table['00']))
        self.assertTrue(q(self.table['01']))
        self.assertTrue(q(self.table['10']))
        self.assertFalse(q(self.table['11']))

    def test_built_in_eq(self):
        """Test built-in lookup `eq` and `exact`."""
        for i, q in enumerate([
            Q(name='John Smith'),
            Q(name__eq='John Smith'),
            Q(name__exact='John Smith'),
        ]):
            with self.subTest(i=i):
                self.assertTrue(q(self.record_1))
                self.assertFalse(q(self.record_2))

    def test_built_in_ne(self):
        """Test built-in lookup `ne` and `neq`."""
        for i, q in enumerate([
            Q(name__ne='John Smith'),
            Q(name__neq='John Smith'),
        ]):
            with self.subTest(i=i):
                self.assertFalse(q(self.record_1))
                self.assertTrue(q(self.record_2))

    def test_built_in_is(self):
        """Test built-in lookup `is`."""
        q = Q(weapon__is=None)
        self.assertTrue(q(self.record_1))
        self.assertFalse(q(self.record_2))

    def test_built_in_is_not(self):
        """Test built-in lookup `is_not`."""
        q = Q(weapon__is_not=None)
        self.assertFalse(q(self.record_1))
        self.assertTrue(q(self.record_2))

    def test_built_in_contains(self):
        """Test built-in lookup `contains`."""
        q = Q(name__contains='John')
        self.assertTrue(q(self.record_1))
        self.assertFalse(q(self.record_2))

        q = Q(tags__contains='Human')
        self.assertTrue(q(self.dict_data))

    def test_built_in_in(self):
        """Test built-in lookup `in`."""
        q = Q(weapon__in=[None, 'Gun'])
        self.assertTrue(q(self.record_1))
        self.assertFalse(q(self.record_2))

    def test_built_in_lt(self):
        """Test built-in lookup `lt`."""
        for score in [80, 95, 90, 97, 100]:
            with self.subTest(score=score):
                q = Q(score__lt=score)
                self.assertEqual(q(self.record_1), self.record_1.score < score)
                self.assertEqual(q(self.record_2), self.record_2.score < score)

    def test_built_in_le(self):
        """Test built-in lookup `le` and `lte`."""
        for score in [80, 95, 90, 97, 100]:
            with self.subTest(score=score):
                for i, q in enumerate([
                    Q(score__le=score),
                    Q(score__lte=score),
                ]):
                    with self.subTest(i=i):
                        self.assertEqual(q(self.record_1), self.record_1.score <= score)
                        self.assertEqual(q(self.record_2), self.record_2.score <= score)

    def test_built_in_gt(self):
        """Test built-in lookup `gt`."""
        for score in [80, 95, 90, 97, 100]:
            with self.subTest(score=score):
                q = Q(score__gt=score)
                self.assertEqual(q(self.record_1), self.record_1.score > score)
                self.assertEqual(q(self.record_2), self.record_2.score > score)

    def test_built_in_ge(self):
        """Test built-in lookup `ge` and `gte`."""
        for score in [80, 95, 90, 97, 100]:
            with self.subTest(score=score):
                for i, q in enumerate([
                    Q(score__ge=score),
                    Q(score__gte=score),
                ]):
                    with self.subTest(i=i):
                        self.assertEqual(q(self.record_1), self.record_1.score >= score)
                        self.assertEqual(q(self.record_2), self.record_2.score >= score)

    def test_built_in_divisible_by(self):
        """Test built-in lookup `divisible_by`."""
        q = Q(score__divisible_by=5)
        self.assertTrue(q(self.record_1))
        self.assertFalse(q(self.record_2))

    def test_built_in_range(self):
        """Test built-in lookup `range`, `inrange` and `in_range`."""
        for r in [
            (60, 80),
            (80, 84),
            (80, 85),
            (80, 90),
            (85, 90),
            (86, 95),
            (90, 99),
        ]:
            with self.subTest(range=r):
                for i, q in enumerate([
                    Q(score__range=r),
                    Q(score__inrange=r),
                    Q(score__in_range=r),
                ]):
                    with self.subTest(i=i):
                        self.assertEqual(q(self.record_1), r[0] <= self.record_1.score <= r[1])

    def test_built_in_isnull(self):
        """Test built-in lookup `isnull` and `is_null`."""
        for i, q in enumerate([
            Q(weapon__isnull=True),
            Q(weapon__is_null=True),
        ]):
            with self.subTest(i=i):
                self.assertTrue(q(self.record_1))
                self.assertFalse(q(self.record_2))

        for i, q in enumerate([
            Q(weapon__isnull=False),
            Q(weapon__is_null=False),
        ]):
            with self.subTest(i=i):
                self.assertFalse(q(self.record_1))
                self.assertTrue(q(self.record_2))

    def test_built_in_startswith(self):
        """Test built-in lookup `startswith`."""
        q = Q(name__startswith='John')
        self.assertTrue(q(self.record_1))
        self.assertFalse(q(self.record_2))

    def test_built_in_endswith(self):
        """Test built-in lookup `endswith`."""
        q = Q(name__endswith='Smith')
        self.assertTrue(q(self.record_1))
        self.assertFalse(q(self.record_2))

    def test_built_in_regex(self):
        """Test built-in lookup `regex`."""
        q = Q(name__regex=r'\w+ Smith')
        self.assertTrue(q(self.record_1))
        self.assertFalse(q(self.record_2))

    def test_built_in_iregex(self):
        """Test built-in lookup `iregex`."""
        q = Q(name__iregex=r'\w+ smith')
        self.assertTrue(q(self.record_1))
        self.assertFalse(q(self.record_2))

    def test_built_in_isinstance(self):
        """Test built-in lookup `isinstance`."""
        q = Q(name__isinstance=dict)
        self.assertFalse(q(self.record_1))
        self.assertTrue(q(self.dict_data))

    def test_built_in_issubclass(self):
        """Test built-in lookup `issubclass`."""
        q = Q(cls__issubclass=object)
        self.assertTrue(q(self.dict_data))
        q = Q(cls__issubclass=list)
        self.assertFalse(q(self.dict_data))


class TestPipeline(unittest.TestCase):
    """Test for `Pipeline`."""

    def test_init_with_default_arguments(self):
        """Test `Pipeline.__init__` with a default arguments."""
        p = Pipeline()
        self.assertEqual(list(p), [])

        p = Pipeline([1, 2, 3, 4])
        self.assertEqual(list(p), [1, 2, 3, 4])

        p = Pipeline(func=lambda x: map(str, x))
        self.assertEqual(list(p), [])

    def test_source_behavior(self):
        """Test `Pipeline` behavior about source."""
        it = iter(range(10))
        p = Pipeline(it)

        a = [next(it) for _ in range(5)]
        b = list(p)
        c = list(p)

        self.assertIs(p.source, it)
        self.assertEqual(a, [0, 1, 2, 3, 4])
        self.assertEqual(b, [5, 6, 7, 8, 9])
        self.assertTrue(not c)

    def test_func(self):
        """Test `Pipeline.func`."""

        def transform(iterable):
            return sorted(iterable)

        p = Pipeline(func=transform)
        func = p.func
        self.assertEqual(
            func([4, 3, 1, 2, 0]),
            [0, 1, 2, 3, 4],
        )

    def test_copy(self):
        """Test `Pipeline.copy`."""
        p = Pipeline(range(5))

        q = p.copy()
        self.assertIs(q.source, p.source)
        self.assertEqual(list(q), list(p))
        self.assertIsNot(q, p)

        q = p.copy(source=(3, 5, 7, 9))
        self.assertIsNot(q.source, p.source)
        self.assertEqual(list(q), [3, 5, 7, 9])
        self.assertIsNot(q, p)

        q = p.copy(func=lambda x: reversed(sorted(x)))
        self.assertIs(q.source, p.source)
        self.assertEqual(list(q), [4, 3, 2, 1, 0])
        self.assertIsNot(q, p)

    def test_compose(self):
        """Test `Pipeline.compose`."""
        p = Pipeline(
            range(5),
            lambda x: map(lambda n: n * 2, x)
        )
        q = p.compose(lambda x: map(lambda n: n + 3, x))
        self.assertIsNot(q, p)
        self.assertEqual(list(p), [0, 2, 4, 6, 8])
        self.assertEqual(list(q), [6, 8, 10, 12, 14])

    def test_and_then(self):
        """Test `Pipeline.and_then`."""
        p = Pipeline(
            range(5),
            lambda x: map(lambda n: n * 2, x)
        )
        q = p.and_then(lambda x: map(lambda n: n + 3, x))
        self.assertIsNot(q, p)
        self.assertEqual(list(p), [0, 2, 4, 6, 8])
        self.assertEqual(list(q), [3, 5, 7, 9, 11])

    def test_filter(self):
        """Test `Pipeline.filter`."""
        p = Pipeline(range(5))
        q = p.filter(lambda x: x % 2 == 0)
        self.assertIsNot(q, p)
        self.assertEqual(list(p), [0, 1, 2, 3, 4])
        self.assertEqual(list(q), [0, 2, 4])

        q = p.filter(lambda x: x % 2 == 0 and x % 3 != 1)
        self.assertEqual(list(q), [0, 2])

    def test_map(self):
        """Test `Pipeline.map`."""
        p = Pipeline(range(5))
        q = p.map(lambda x: x * 3)
        self.assertIsNot(q, p)
        self.assertEqual(list(p), [0, 1, 2, 3, 4])
        self.assertEqual(list(q), [0, 3, 6, 9, 12])


class TestQuery(unittest.TestCase):
    """Test for `Query`."""

    def setUp(self):
        Record = namedtuple(
            'Record',
            ['id', 'score', 'birthday'],
        )
        self.record_cls = Record
        self.data = [
            Record(1, 40, date(1993, 12, 3)),
            Record(2, 70, date(1991, 2, 23)),
            Record(3, 60, date(1999, 7, 6)),
            Record(4, 90, date(1996, 8, 17)),
            Record(5, 80, date(1997, 2, 8)),
        ]

    def test_filter(self):
        """Test `Query.filter`."""
        record = self.record_cls
        q = Query(self.data)

        q2 = q.filter(lambda r: r.score < 60)
        self.assertIsNot(q, q2)
        self.assertEqual(
            list(q2),
            [record(1, 40, date(1993, 12, 3))],
        )

        q3 = q.filter(score__lt=60)
        self.assertEqual(
            list(q3),
            [record(1, 40, date(1993, 12, 3))],
        )

        q4 = q.filter(Q(score__lt=60))
        self.assertEqual(
            list(q4),
            [record(1, 40, date(1993, 12, 3))],
        )

        q5 = q.filter(Q(score__gte=70), birthday__month=2)
        self.assertEqual(
            list(q5),
            [
                record(2, 70, date(1991, 2, 23)),
                record(5, 80, date(1997, 2, 8)),
            ],
        )

    def test_exclude(self):
        """Test `Query.exclude`."""
        record = self.record_cls
        q = Query(self.data)

        q2 = q.exclude(lambda r: r.score >= 60)
        self.assertIsNot(q, q2)
        self.assertEqual(
            list(q2),
            [record(1, 40, date(1993, 12, 3))],
        )

        q3 = q.exclude(score__gte=60)
        self.assertEqual(
            list(q3),
            [record(1, 40, date(1993, 12, 3))],
        )

        q4 = q.exclude(Q(score__gte=60))
        self.assertEqual(
            list(q4),
            [record(1, 40, date(1993, 12, 3))],
        )

        q5 = q.exclude(Q(score__gte=70), birthday__month=2)
        self.assertEqual(
            list(q5),
            [
                record(1, 40, date(1993, 12, 3)),
                record(3, 60, date(1999, 7, 6)),
                record(4, 90, date(1996, 8, 17)),
            ],
        )

    def test_sort(self):
        """Test `Query.sort`."""
        record = self.record_cls
        q = Query(self.data)

        q2 = q.sort(key=lambda r: r.score, reverse=True)
        self.assertIsNot(q, q2)
        self.assertEqual(
            list(q2),
            [
                record(4, 90, date(1996, 8, 17)),
                record(5, 80, date(1997, 2, 8)),
                record(2, 70, date(1991, 2, 23)),
                record(3, 60, date(1999, 7, 6)),
                record(1, 40, date(1993, 12, 3)),
            ],
        )

    def test_sort_by(self):
        """Test `Query.sort_by`."""
        record = self.record_cls
        q = Query(self.data)

        q2 = q.sort_by('score')
        self.assertIsNot(q, q2)
        self.assertEqual(
            list(q2),
            [
                record(1, 40, date(1993, 12, 3)),
                record(3, 60, date(1999, 7, 6)),
                record(2, 70, date(1991, 2, 23)),
                record(5, 80, date(1997, 2, 8)),
                record(4, 90, date(1996, 8, 17)),
            ],
        )

        q3 = q.sort_by('birthday__month', '-score')
        self.assertEqual(
            list(q3),
            [
                record(5, 80, date(1997, 2, 8)),
                record(2, 70, date(1991, 2, 23)),
                record(3, 60, date(1999, 7, 6)),
                record(4, 90, date(1996, 8, 17)),
                record(1, 40, date(1993, 12, 3)),
            ],
        )

        q4 = q.sort_by(lambda r: r.birthday.month, '-score')
        self.assertEqual(
            list(q4),
            [
                record(5, 80, date(1997, 2, 8)),
                record(2, 70, date(1991, 2, 23)),
                record(3, 60, date(1999, 7, 6)),
                record(4, 90, date(1996, 8, 17)),
                record(1, 40, date(1993, 12, 3)),
            ],
        )

        qr = Query(range(100)).sort_by('?')
        self.assertNotEqual(list(qr), list(range(100)))  # It is almost impossible to be equal.

    def test_reverse(self):
        """Test `Query.reverse`."""
        record = self.record_cls
        q = Query(self.data)

        q2 = q.reverse()
        self.assertIsNot(q, q2)
        self.assertEqual(
            list(q2),
            [
                record(5, 80, date(1997, 2, 8)),
                record(4, 90, date(1996, 8, 17)),
                record(3, 60, date(1999, 7, 6)),
                record(2, 70, date(1991, 2, 23)),
                record(1, 40, date(1993, 12, 3)),
            ],
        )

    def test_distinct(self):
        """Test `Query.distinct`."""
        q = Query([1, 3, 2, 3, 5, 4, 1, 4])

        q2 = q.distinct()
        self.assertIsNot(q2, q)
        self.assertEqual(list(q2), [1, 3, 2, 5, 4])

        q3 = q.distinct(key=lambda x: x % 3)
        self.assertEqual(list(q3), [1, 3, 2])

    def test_prepend(self):
        """Test `Query.prepend`."""
        q = Query([1, 2, 3, 4, 5])

        q2 = q.prepend([6, 7], [8, 9])
        self.assertIsNot(q2, q)
        self.assertEqual(list(q), [1, 2, 3, 4, 5])
        self.assertEqual(list(q2), [6, 7, 8, 9, 1, 2, 3, 4, 5])

        q3 = q.prepend()
        self.assertEqual(list(q3), [1, 2, 3, 4, 5])

    def test_append(self):
        """Test `Query.append`."""
        q = Query([1, 2, 3, 4, 5])

        q2 = q.append([6, 7], [8, 9])
        self.assertIsNot(q2, q)
        self.assertEqual(list(q), [1, 2, 3, 4, 5])
        self.assertEqual(list(q2), [1, 2, 3, 4, 5, 6, 7, 8, 9])

        q3 = q.append()
        self.assertEqual(list(q3), [1, 2, 3, 4, 5])

    def test_slice(self):
        """Test `Query.slice`."""
        q = Query(range(10))

        q2 = q.slice(5)
        self.assertIsNot(q2, q)
        self.assertEqual(list(q2), [0, 1, 2, 3, 4])

        q3 = q.slice(4, 8)
        self.assertEqual(list(q3), [4, 5, 6, 7])

        q4 = q.slice(4, 2)
        self.assertEqual(list(q4), [])

        q5 = q.slice(2, 7, 3)
        self.assertEqual(list(q5), [2, 5])

    def test_getitem(self):
        """Test `Query.__getitem__`."""
        q = Query(range(10))

        self.assertEqual(q[5], 5)
        self.assertEqual(q[-3], 7)
        with self.assertRaises(IndexError):
            print(q[100])

        q2 = q[2:7]
        self.assertIsNot(q2, q)
        self.assertEqual(list(q2), [2, 3, 4, 5, 6])

        with self.assertRaises(TypeError):
            print(q['first'])

    def test_head(self):
        """Test `Query.head`."""
        q = Query(range(10))

        q2 = q.head(3)
        self.assertIsNot(q2, q)
        self.assertEqual(list(q2), [0, 1, 2])

        q3 = q.head(0)
        self.assertEqual(list(q3), [])

    def test_tail(self):
        """Test `Query.tail`."""
        q = Query(range(10))

        q2 = q.tail(3)
        self.assertIsNot(q2, q)
        self.assertEqual(list(q2), [7, 8, 9])

        q3 = q.tail(0)
        self.assertEqual(list(q3), [])

    def test_repeat(self):
        """Test `Query.repeat`."""
        q = Query(range(5))

        q2 = q.repeat(None)
        self.assertIsNot(q2, q)
        count = 0
        for _ in q2:
            count += 1
            if count > 99999:
                break
        self.assertGreater(count, 99999)

        for times in [-5, 0, 1]:
            with self.subTest(times=times):
                q3 = q.repeat(times)
                self.assertIsNot(q3, q)
                self.assertEqual(list(q3), [0, 1, 2, 3, 4])

        q4 = q.repeat(3)
        self.assertIsNot(q4, q)
        self.assertEqual(list(q4), [0, 1, 2, 3, 4] * 3)


class TestStream(unittest.TestCase):
    """Test for `Stream`."""

    def test_init(self):
        """Test `Stream.__init__`."""
        s = Stream(range(5))
        self.assertEqual(list(s), [0, 1, 2, 3, 4])

        s = Stream()
        self.assertEqual(list(s), [])

    def test_lshift(self):
        """Test `Stream.__lshift__`."""
        s = Stream(range(5))
        s2 = s << range(3)
        self.assertIs(s2, s)
        self.assertEqual(list(s), [0, 1, 2, 3, 4, 0, 1, 2])

    def test_getitem(self):
        """Test `Stream.__getitem__`."""
        s = Stream() << range(5)

        self.assertEqual(s[2], 2)
        with self.assertRaises(ValueError):
            print(s[-1])
        with self.assertRaises(IndexError):
            print(s[99])

        self.assertEqual(list(s[:3]), [0, 1, 2])
        self.assertEqual(list(s[::2]), [0, 2, 4])
        self.assertEqual(list(s[::-2]), [4, 2, 0])
        self.assertEqual(list(s[3::-3]), [3, 0])

        with self.assertRaises(TypeError):
            print(s[0, 1])

    def test_elements_stored(self):
        """Test the behavior of storing elements."""

        def gen():
            yield 3
            yield 4
            yield 5

        s = Stream() << gen()
        self.assertEqual(
            list(chain(s, s)),
            [3, 4, 5, 3, 4, 5],
        )
