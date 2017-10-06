import os
from urllib import parse
import psycopg2


def get_db_conn_and_cursor(config=None):
    """
    Obtains a connection and cursor object to the PostgresSQL database

    Args:
        config: (dict) Contains configuration variables

    Returns: psycopg2.extensions.connection, psycopg2.extensions.cursor
    """
    if config == None:
        parse.uses_netloc.append('postgres')
        config = {'PG_URL': parse.urlparse(os.environ["DATABASE_URL"])}
    conn = psycopg2.connect(
        database=config['PG_URL'].path[1:],
        user=config['PG_URL'].username,
        password=config['PG_URL'].password,
        host=config['PG_URL'].hostname,
        port=config['PG_URL'].port
    )
    cur = conn.cursor()

    return conn, cur
