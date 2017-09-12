import unittest
from utils import u_views


class HelpersTestCase(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_is_valid_number(self):
        """
        Not the most robust test, but it will do for now
        """
        self.assertEqual("+18505555555", u_views.is_valid_number("8505555555"))
        self.assertFalse(u_views.is_valid_number("(850)555-5555"))

    # Test we can connect to database and that proper tables/schema exist

    def test_sign_up_user(self):
        pass

    def test_unsubscribe_user(self):
        pass
