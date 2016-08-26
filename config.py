import os
import urllib.parse
import psycopg2

WTF_CSRF_ENABLED = True
SECRET_KEY = 'x,?\x0f\xce\x99a\xe0\x96\xca\xa9\xb4\xb18U\x84\xfbP\xf2DDg*\x96'

urllib.parse.uses_netloc.append("postgres")
PG_URL = urllib.parse.urlparse(os.environ["DATABASE_URL"])

PG_CONN = psycopg2.connect(
    database=PG_URL.path[1:],
    user=PG_URL.username,
    password=PG_URL.password,
    host=PG_URL.hostname,
    port=PG_URL.port
)

PG_CUR = PG_CONN.cursor()