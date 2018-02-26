from flask import Flask, session, redirect, url_for, escape, request, render_template, flash, send_from_directory
from nebula import app
from nebula.services import ldapuser

# set the secret key.  keep this really secret:
app.secret_key = app.config['SECRET_KEY']
app.ssh_secret = app.config['SSH_SECRET']

import nebula.services.session
import nebula.extensions.jinja
import nebula.cli.aws
import nebula.cli.maintenance
import nebula.routes.admin
import nebula.routes.auth
import nebula.routes.errors
import nebula.routes.feedback
import nebula.routes.profiles
import nebula.routes.servers
import nebula.routes.ssh_keys
from nebula.services import aws
import nebula.services.notifications
import nebula.services.external_api


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
