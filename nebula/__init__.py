from flask import Flask
import os
import requests
import yaml


app = Flask(__name__)


def get_secret(secret_name):
    import boto3
    import json
    if 'AWS_SECRETS_REGION' in os.environ:
        region = os.environ['AWS_SECRETS_REGION']
    else:
        r = requests.get('http://169.254.169.254/latest/dynamic/instance-identity/document')
        r.raise_for_status()
        data = r.json()
        region = data['region']
    client = boto3.client(
        service_name='secretsmanager',
        region_name=region
    )

    # Decrypted secret using the associated KMS CMK
    # Depending on whether the secret was a string or binary, one of these fields will be populated
    get_secret_value_response = client.get_secret_value(SecretId=secret_name)
    if 'SecretString' in get_secret_value_response:
        secret = get_secret_value_response['SecretString']
    else:
        secret = get_secret_value_response['SecretBinary'].decode("utf-8")
    return yaml.safe_load(secret)


if 'SETTINGS' in os.environ:
    if os.path.isfile(os.environ['SETTINGS']):
        with open(os.environ['SETTINGS'], 'r') as stream:
            app.config.update(yaml.safe_load(stream))
    else:
        print('Unable to open settings file %s' % (os.environ['SETTINGS']))


# Can be used to store entire config in AWS Secrets Manager, or can be combined
# with file based config to provide some (but not all) settings. Can't be used
# with the AWS Concole- the config must by uploaded using the API.
if 'AWS_SECRETS_SETTINGS' in os.environ:
    aws_secret_name = os.environ['AWS_SECRETS_SETTINGS']
    aws_config = get_secret(aws_secret_name)
    app.config.update(aws_config)

# If enabled in the existing (typically file based) settings then some specific
# settings will be looked for in the AWS Secrets Manager. This is the only AWS
# Console compatible option.
if 'aws_secret_name' in app.config:
    secret_mapping = {
        'bind_password': 'ldap',
        'bind_dn': 'ldap',
        'secret_key': 'general',
        'ssh_secret': 'api',
        'username': 'postgres',
        'password': 'postgres',
    }
    aws_secrets = aws.get_secret(app.config['aws_secret_name'])
    for key, value in aws_secrets.items():
        if key in secret_mapping:
            app.config[secret_mapping[key]][key] = value


# if enabled logs will be sent to LogDNA via ingest api.
if 'LOGDNA_INGESTION_KEY' in os.environ:
    import logging
    from logdna import LogDNAHandler

    log = logging.getLogger('nebula')

    logdna_handler = LogDNAHandler(
        os.getenv('LOGDNA_INGESTION_KEY'),
        {'app': 'Nebula', 'include_standard_meta': True})
    log_level = logging.DEBUG if 'DEBUG' in os.environ else logging.INFO
    logdna_handler.setLevel(log_level)
    log.addHandler(logdna_handler)
    log.info('added logdna handler..')


if 'general' not in app.config:
    app.config['general'] = {
        'filecache': '/tmp/nebula',
        'secret_key': 'changeme'
    }

if 'site_name' not in app.config['general']:
    app.config['general']['site_name'] = 'nebula'


# Initialize Celery
from celery import Celery
if 'celery' in app.config:
    celery = Celery(__name__, broker=app.config['celery']['broker'], backend=app.config['celery']['results'])
else:
    celery = Celery(__name__)

import nebula.nebula
