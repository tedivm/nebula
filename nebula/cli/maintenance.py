import os, sys
from datetime import datetime, timedelta
import subprocess
import click
from nebula import app
import shutil
from nebula.models import users
from nebula.services import notifications

@app.cli.command()
def clean_sessions():
    sessiondir = app.config['general']['filecache'] + '/sessions'
    for dirpath, dirnames, filenames in os.walk(sessiondir):
        for file in filenames:
            curpath = os.path.join(dirpath, file)
            file_modified = datetime.fromtimestamp(os.path.getmtime(curpath))
            if datetime.now() - file_modified > timedelta(hours=336):
                os.remove(curpath)


@app.cli.command()
def clear_cache():
    cachedata = app.config['general']['filecache'] + '/data'
    shutil.rmtree(cachedata)


@app.cli.command()
@click.argument('user')
def reset_2fa(user):
    users.save_user_token(user, None)


@app.cli.command()
@click.argument('recipient')
def test_email(recipient):
    click.echo('Attempting to send email to %s' % (recipient,))
    subject = 'Nebula Test Message'
    text = 'This is a test of the nebula notification system'
    notifications.send_notification_email(subject, text, recipient)


@app.cli.command()
def notify_users():
    notifications.notify_users()
