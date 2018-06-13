import os, sys
from datetime import datetime, timedelta
import subprocess
import click
from flask import Flask, session, redirect, url_for, escape, request, render_template, flash, send_from_directory
from nebula import app
from nebula.services.cache import cache
from nebula.services import aws
from time import time

@app.cli.command()
def list_instance_types():
    print(aws.get_instance_types())


@app.cli.command()
def shutdown_expired_instances():
    aws.shutdown_expired_instances()


@app.cli.command()
@click.argument('settings_path')
@click.argument('secret_name')
def config_to_aws_sm(settings_path, secret_name):
    if not os.path.isfile(settings_path):
        print('Unable to find settings file at %s' % (settings_path))
        sys.exit(1)

    with open(settings_path, 'r') as stream:
        config_string = stream.read()
        set_secret(secret_name, config_string)


def set_secret(secret_name, secret_string):
    client = boto3.client(
        service_name='secretsmanager',
    )

    try:
        response = client.create_secret(
            Name=secret_name,
            Description='Nebula Configuration File',
            SecretString=secret_string,
            Tags=[
                {'Key': 'nebula', 'Value': 'true'}
            ]
        )
    except client.exceptions.ResourceExistsException:
        response = client.put_secret_value(
            SecretId=secret_name,
            SecretString=secret_string,
        )
