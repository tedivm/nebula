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
