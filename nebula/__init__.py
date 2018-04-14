from flask import Flask
import os
import yaml
app = Flask(__name__)

if 'SETTINGS' in os.environ:
    with open(os.environ['SETTINGS'], 'r') as stream:
        app.config.update(yaml.load(stream))

# Initialize Celery
from celery import Celery
celery = Celery(__name__, broker=app.config['celery']['broker'], backend=app.config['celery']['results'])

import nebula.nebula
