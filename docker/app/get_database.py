#!/usr/bin/env python3

import os
import yaml

if 'AWS_SECRETS_SETTINGS' in os.environ:
    import boto3
    import json
    client = boto3.client(
        service_name='secretsmanager'
    )

    # Decrypted secret using the associated KMS CMK
    # Depending on whether the secret was a string or binary, one of these fields will be populated
    get_secret_value_response = client.get_secret_value(SecretId=secret_name)
    if 'SecretString' in get_secret_value_response:
        secret = get_secret_value_response['SecretString']
    else:
        secret = get_secret_value_response['SecretBinary'].decode("utf-8")
    settings = yaml.load(secret)
    print(settings['postgres']['host'])

elif 'SETTINGS' in os.environ:
    with open(os.environ['SETTINGS'], 'r') as stream:
        settings = yaml.load(stream)
        print(settings['postgres']['host'])
