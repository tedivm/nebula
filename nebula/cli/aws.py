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
    curtimestamp = int(time())
    instances = aws.get_instance_list(state='running', terminated=False)
    for instance in instances:
        print(instance)
        tags = aws.get_tags_from_aws_object(instance)
        print('Beginning check of %s' % (instance.instance_id,))
        if 'Shutdown' in tags and tags['Shutdown'].isdigit():
            shutdown = int(tags['Shutdown'])
            print("%s (%s < %s)" % (instance.instance_id, curtimestamp, shutdown))
            if shutdown <= curtimestamp:
                print("Shutting down instance %s" % (instance.instance_id))
                aws.stop_instance.delay(instance.instance_id)
