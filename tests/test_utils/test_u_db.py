import os
import psycopg2
import unittest
from urllib import parse

from utils.u_db import get_db_conn_and_cursor

class UtilsTestCase(unittest.TestCase):
    def setUp(self):
        parse.uses_netloc.append('postgres')
        config = {'PG_URL': parse.urlparse(os.environ["DATABASE_URL"])}
        self.conn = psycopg2.connect(
            database=config['PG_URL'].path[1:],
            user=config['PG_URL'].username,
            password=config['PG_URL'].password,
            host=config['PG_URL'].hostname,
            port=config['PG_URL'].port
        )
        self.cur = self.conn.cursor()


        self.data = []
        with open('test_data/test_db_schedule.tsv', 'r') as fh:
            for line in fh.readlines():
                self.data.append(line.split('\t'))

        # TODO: Need to remove the call to now() when loading dummy data, as
        # that will actually put in the current timestamp instead of a dummy one
        for row in self.data:
            self.cur.execute("INSERT INTO schedule (type, brief, edt, rtb, "
                       "instructor, student, event, remarks, location, date, timestamp) "
                       "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, now())",
                       [row[1], row[2], row[3], row[4], row[5],
                        row[6], row[7], row[8], row[9], row[10]],)

        self.conn.commit()


    def tearDown(self):
        self.cur.execute("DELETE FROM schedule WHERE id > 0;")
        self.conn.commit()
        self.cur.close()
        self.conn.close()

    def test_get_db_conn_and_cursor(self):
        a = get_db_conn_and_cursor()