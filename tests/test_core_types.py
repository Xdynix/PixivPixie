"""Unittest for `pixiv_pixie.core.types`."""

import unittest

from pixiv_pixie.core.types import Illust


class TestIllust(unittest.TestCase):
    """Tests for `Illust`."""

    def test_shape(self):
        """Test `Illust.shape` property."""
        self.assertEqual(
            Illust(width=300, height=200).shape,
            (300, 200),
        )

    def test_aspect_ratio(self):
        """Test `Illust.aspect_ratio` property."""
        self.assertEqual(
            Illust(width=300, height=200).aspect_ratio,
            1.5,
        )
        self.assertEqual(
            Illust(width=300, height=0).aspect_ratio,
            0.,
        )
