from celery.schedules import crontab
from flask import Flask, session, redirect, url_for, request
from nebula import app, celery
from nebula.services import ldapuser

# set the secret key.  keep this really secret:
app.secret_key = app.config['general']['secret_key']

if 'api' in app.config:
    app.ssh_secret = app.config['api']['ssh_secret']

import nebula.services.session
import nebula.extensions.jinja
import nebula.cli.aws
import nebula.cli.maintenance
import nebula.cli.tokens
import nebula.routes.admin
import nebula.routes.api
import nebula.routes.auth
import nebula.routes.errors
import nebula.routes.feedback
import nebula.routes.profiles
import nebula.routes.servers
import nebula.routes.ssh_keys
import nebula.routes.tokens
from nebula.services import aws
from nebula.services import notifications

if not app.secret_key or app.secret_key is 'CHANGE_THIS_PASSWORD':
    raise ValueError('The `secret key` setting must be set before the application can run.')


@celery.on_after_finalize.connect
def setup_periodic_tasks(sender, **kwargs):
    sender.add_periodic_task(65.0, aws.shutdown_expired_instances.s(), name='AWS Scheduled Shutdowns')
    sender.add_periodic_task(301, aws.tag_active_instances.s(), name='AWS Active Instance Tags')
    sender.add_periodic_task(
        crontab(hour=4, minute=30),
        notifications.notify_users.s(),
        name='AWS Active Machine Notifications'
    )


@app.route('/')
def index():
    if 'username' in session:
        if ldapuser.is_admin(session['username']):
            return redirect(url_for('admin_dashboard'))
        else:
            return redirect(url_for('server_list'))
    else:
        return redirect(url_for('login'))


@app.after_request
def add_header(response):
    if 'Cache-Control' not in response.headers:
        response.headers['Cache-Control'] = 'private, no-store, no-cache, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
    return response
