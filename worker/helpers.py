import os
import psycopg2
from urllib import parse


def get_db_conn_and_cursor():
    """
    Obtains a connection and cursor object to the PostgresSQL database

    Args:
        config: (dict) Contains configuration variables

    Returns: psycopg2.extensions.connection, psycopg2.extensions.cursor
    """
    parse.uses_netloc.append("postgres")

    url = parse.urlparse(os.environ["DATABASE_URL"])
    conn = psycopg2.connect(
        database=url.path[1:],
        user=url.username,
        password=url.password,
        host=url.hostname,
        port=url.port
    )
    cur = conn.cursor()

    return conn, cur
