from psycopg2 import IntegrityError
import unittest
from utils import u_db
from worker.update_confirmation_codes import run_conf_code_update


class ConfirmationCodesTestCase(unittest.TestCase):
    def setUp(self):
        self.conn, self.cur = u_db.get_db_conn_and_cursor()
        try:
            self.cur.execute(
                "INSERT INTO unverified (phone, provider, lname, fname, confcode, "\
                    "datetime) VALUES (%s, %s, %s, %s, %s, current_timestamp);",
                ['+18505551111', 'verizon', 'CONFCODETEST1', 'TEST', '1111']
            )
            self.cur.execute(
                "INSERT INTO unverified (phone, provider, lname, fname, confcode, "\
                    "datetime) VALUES (%s, %s, %s, %s, %s, current_timestamp - "\
                    "INTERVAL '1 day' - INTERVAL '5 minutes');",
                ['+18505552222', 'verizon', 'CONFCODETEST2', 'TEST', '2222']
            )
            self.conn.commit()
        except IntegrityError as e:
            # Lines already in database
            self.conn.rollback()

        self.cur.execute("SELECT * FROM unverified WHERE fname LIKE 'TEST';")
        self.assertIsNotNone(self.cur.fetchone())


    def tearDown(self):
        self.cur.execute(
            "DELETE FROM unverified WHERE lname LIKE 'CONFCODETEST1'")
        self.cur.execute(
            "DELETE FROM unverified WHERE lname LIKE 'CONFCODETEST2'")
        self.conn.commit()

        self.cur.execute("SELECT * FROM unverified WHERE fname LIKE 'TEST';")
        self.assertIsNone(self.cur.fetchone())

        self.cur.close()
        self.conn.close()


    def test_run_conf_code_update(self):
        run_conf_code_update()

        self.cur.execute(
            "SELECT * FROM unverified WHERE lname LIKE 'CONFCODETEST2';")
        self.assertIsNone(self.cur.fetchone())

        self.cur.execute(
            "SELECT * FROM unverified WHERE lname LIKE 'CONFCODETEST1';")
        self.assertIsNotNone(self.cur.fetchone())
