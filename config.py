import os
import urllib.parse

urllib.parse.uses_netloc.append("postgres")
PG_URL = urllib.parse.urlparse(os.environ["DATABASE_URL"])
SECRET_KEY = os.environ["SECRET_KEY"]
TWILIO_ACCOUNT_SID = os.environ["TWILIO_ACCOUNT_SID"]
TWILIO_AUTH_TOKEN = os.environ["TWILIO_AUTH_TOKEN"]
WTF_CSRF_ENABLED = True