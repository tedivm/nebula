#!/usr/bin/env python
from migrate.versioning.shell import main
import os
from importlib.machinery import SourceFileLoader
from migrate.exceptions import DatabaseAlreadyControlledError
import yaml

def get_secret(secret_name):
    import boto3
    import json

    if 'AWS_SECRETS_REGION' in os.environ:
        region = os.environ['AWS_SECRETS_REGION']
    else:
        import requests
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
    return yaml.load(secret)

if 'SETTINGS' in os.environ:
    if os.path.isfile(os.environ['SETTINGS']):
        with open(os.environ['SETTINGS'], 'r') as stream:
            settings = yaml.load(stream)['postgres']

if 'AWS_SECRETS_SETTINGS' in os.environ:
    aws_secret_name = os.environ['AWS_SECRETS_SETTINGS']
    aws_config = get_secret(aws_secret_name)
    settings = aws_config['postgres']


if __name__ == '__main__':
    db_url = 'postgresql://%s:5432/%s?user=%s&password=%s' % (settings['host'], settings['database'], settings['username'], settings['password'])
    try:
        main(url=db_url, repository='db', debug='False')
    except DatabaseAlreadyControlledError:
        exit(0)
