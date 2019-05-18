"""Unittest for `pixiv_pixie.utils.singleton`."""

from doctest import DocTestSuite

from pixiv_pixie.utils import singleton


def load_tests(_, tests, __):
    """Load doctests."""
    tests.addTests(DocTestSuite(singleton))
    return tests
