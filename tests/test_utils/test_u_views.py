from app import app
import unittest
from utils import u_views
from utils import u_db

class HelpersTestCase(unittest.TestCase):
    def setUp(self):
        self.conn, self.cur = u_db.get_db_conn_and_cursor(app.config)
        self.phone = '+16665551111'
        self.provider = 'verizon'

    def tearDown(self):
        self.cur.execute("DELETE FROM unverified WHERE lname LIKE 'DELETEME';")
        self.conn.commit()
        self.cur.close()
        self.conn.close()

    def test_is_valid_number(self):
        """
        Not the most robust test, but it will do for now
        """
        self.assertEqual("+18505555555", u_views.is_valid_number("8505555555"))
        self.assertFalse(u_views.is_valid_number("(850)555-5555"))

    def test_sign_up_user(self):
        # invalid phone number tests
        self.assertRaises(AssertionError,
                          lambda: u_views.sign_up_user(
                              self.cur, self.conn, '6665551111', 'verizon',
                              'DELETEME', 'fname'))
        self.assertRaises(AssertionError,
                          lambda: u_views.sign_up_user(
                              self.cur, self.conn, '+166655511112', 'verizon',
                              'DELETEME', 'fname'))
        self.assertRaises(AssertionError,
                          lambda: u_views.sign_up_user(
                              self.cur, self.conn, '+1666555111', 'verizon',
                              'DELETEME', 'fname'))
        self.assertTrue(u_views.sign_up_user(self.cur, self.conn,
                                             '+18505551234','verizon',
                                             'DELETEME', 'fname'))

    def test_send_conf_code(self):
        # Token test just so that it will fail if we change the implementation
        # of this function (i.e. implement Twilio)

        # There is no req in send_conf_code for the confcode to be 16 bits
        self.assertTrue(
            u_views.send_conf_code(
                self.phone, self.provider, "Testing", 16758))

    def test_unsubscribe_user(self):
        pass
