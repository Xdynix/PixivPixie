import unittest
from datetime import datetime, timedelta
from unittest.mock import patch

from pixiv_pixie.core.pixie import Session


class TestSession(unittest.TestCase):
    """Tests for `Session`."""

    def test_create_date_default(self):
        """Test `Session.create_date` default value."""
        # TODO: Try to mock the default factory of Session.create_date.
        session = Session()
        now = datetime.now()
        delta = timedelta(seconds=2)
        self.assertLess(now - delta, session.create_date)
        self.assertLess(session.create_date, now + delta)

    def test_expiration_date(self):
        """Test `Session.expiration_date` property."""
        session = Session(
            access_token='',
            refresh_token='',
            expires_in=4200,
            create_date=datetime(2019, 5, 1, 0, 0, 0),
        )
        self.assertEqual(
            session.expiration_date,
            datetime(2019, 5, 1, 1, 10, 0),
        )

    def test_is_expired(self):
        """Test `Session.is_expired`."""
        may_1st_2019_1200 = datetime(2019, 5, 1, 12, 0, 0)
        may_1st_2019_1300 = datetime(2019, 5, 1, 13, 0, 0)
        with patch('pixiv_pixie.core.pixie.datetime') as mock_datetime:
            mock_datetime.now.return_value = may_1st_2019_1300
            mock_datetime.side_effect = datetime

            session = Session(expires_in=1800, create_date=may_1st_2019_1200)
            self.assertTrue(session.is_expired())

            session = Session(expires_in=3600, create_date=may_1st_2019_1200)
            self.assertTrue(session.is_expired())

            session = Session(expires_in=7200, create_date=may_1st_2019_1200)
            self.assertFalse(session.is_expired())

            session = Session(expires_in=3700, create_date=may_1st_2019_1200)
            self.assertFalse(session.is_expired(delta=0))
            self.assertTrue(session.is_expired())
            self.assertTrue(session.is_expired(delta=900))
