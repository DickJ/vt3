import unittest
from app import helpers


class HelpersTestCase(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_is_valid_number(self):
        """
        Not the most robust test, but it will do for now
        """
        self.assertEqual("+18505555555", helpers.is_valid_number("8505555555"))
        self.assertFalse(helpers.is_valid_number("(850)555-5555"))

    # Test we can connect to database and that proper tables/schema exist