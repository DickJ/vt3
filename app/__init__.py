from flask import Flask
import logging

logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
app.config.from_object('config')

from app import views
