from flask import Flask, session, redirect, url_for, request, render_template, jsonify, make_response, abort
from nebula import app
from nebula.routes.decorators import login_required, admin_required, admin_or_belongs_to_user
from nebula.models import ssh_keys
from nebula.services import export, ldapuser


@app.route('/ssh/create', methods=['GET', 'POST'])
@login_required
def ssh_key_create():
    """Handle GET (render) and POST (submit form to DB) requests at /ssh/create."""
    if request.method == 'POST':
        # Only allow admins to modify username, use session as fallback
        if ldapuser.is_admin(session['username']):
            username = request.form.get('username', session['username'])
        else:
            username = session['username']
        key_name = request.form['key_name']
        ssh_key = request.form['ssh_key']
        ssh_keys.create_new_key(username, key_name, ssh_key)
        return redirect(url_for('ssh_key_list'))
    return render_template('ssh_form.html', ssh_info={})


@app.route('/ssh/list')
@login_required
def ssh_key_list():
    """Handle GET requests at /ssh/list for a user's SSH keys."""
    key_list = ssh_keys.list_ssh_keys(session['username'])
    return render_template('ssh_keys.html', ssh_keys=key_list, admin=None)


@app.route('/ssh/<ssh_key_id>/update', methods=['GET', 'POST'])
@app.route('/ssh/<ssh_key_id>/update/<admin>', methods=['GET', 'POST'])
@admin_or_belongs_to_user
def ssh_key_update(ssh_key_id, admin=None):
    """Handle GET (render form) and POST (update db) requests at /ssh/<id>/update."""
    ssh_info = ssh_keys.get_ssh_key(ssh_key_id)
    if request.method == 'POST':
        # Only allow admins to modify username, use session as fallback
        if ldapuser.is_admin(session['username']):
            username = request.form.get('username', session['username'])
        else:
            username = session['username']
        key_name = request.form.get('key_name', ssh_info['key_name'])
        ssh_key = request.form.get('ssh_key', ssh_info['ssh_key'])
        ssh_keys.update_ssh_key(ssh_key_id, username, key_name, ssh_key)

        # Redirect admin users back to the admin panel
        if admin:
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('ssh_key_list'))

    return render_template('ssh_form.html', ssh_info=ssh_info)


@app.route('/ssh/<ssh_key_id>/remove', methods=['GET', 'POST'])
@app.route('/ssh/<ssh_key_id>/remove/<admin>', methods=['GET', 'POST'])
@admin_or_belongs_to_user
def ssh_key_remove(ssh_key_id, admin=None):
    """Handle GET (confirmation page) and POST (deletions) requests at /ssh/<id>/remove."""
    if request.method == 'POST':
        ssh_keys.remove_ssh_key(ssh_key_id)

        # Redirect admin users back to the admin panel
        if admin:
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('ssh_key_list'))

    return render_template('confirm.html')


@app.route('/ssh/export')
def ssh_key_export():
    """Export ssh keys into a downloadable json file."""
    if 'api' not in app.config or 'ssh_secret' not in app.config['api']:
        abort(404)

    if app.config['api']['ssh_secret'] is 'CHANGE_THIS_PASSWORD':
        abort(500)

    # Verify that request passes in correct shared secret
    if ('sshsecret' not in request.headers or
            request.headers['sshsecret'] != app.config['api']['ssh_secret']):
        abort(401)

    response = make_response(jsonify(export.collect_all_keys()))
    response.headers['Content-Disposition'] = 'attachment'
    return response
