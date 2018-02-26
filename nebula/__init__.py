from flask import Flask
app = Flask(__name__)
app.config.from_envvar('SETTINGS')

# Initialize Celery
from celery import Celery
celery = Celery(__name__, broker=app.config['CELERY_BROKER_URL'], backend=app.config['CELERY_RESULT_URL'])


import nebula.nebula
