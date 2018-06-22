#!/usr/bin/env python3
import boto3
import os
import requests
import json
import yaml

if 'AWS_SECRETS_SETTINGS' in os.environ:
    aws_secret_name = os.environ['AWS_SECRETS_SETTINGS']
    if 'AWS_SECRETS_REGION' in os.environ:
        aws_region = os.environ['AWS_SECRETS_REGION']
    else:
        r = requests.get('http://169.254.169.254/latest/dynamic/instance-identity/document')
        r.raise_for_status()
        data = r.json()
        aws_region = data['region']

    client = boto3.client(
        service_name='secretsmanager',
        region_name=aws_region
    )

    # Decrypted secret using the associated KMS CMK
    # Depending on whether the secret was a string or binary, one of these fields will be populated
    get_secret_value_response = client.get_secret_value(SecretId=aws_secret_name)
    if 'SecretString' in get_secret_value_response:
        secret = get_secret_value_response['SecretString']
    else:
        secret = get_secret_value_response['SecretBinary'].decode("utf-8")
    settings = yaml.load(secret)
    print(settings['postgres']['host'])

elif 'SETTINGS' in os.environ:
    if os.path.isfile(os.environ['SETTINGS']):
        with open(os.environ['SETTINGS'], 'r') as stream:
            settings = yaml.load(stream)
            print(settings['postgres']['host'])
