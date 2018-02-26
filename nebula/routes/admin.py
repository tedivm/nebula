from flask import Flask, session, redirect, url_for, escape, request, render_template, jsonify
from nebula import app
from nebula.routes.decorators import login_required, admin_required
from nebula.services import aws
from nebula.models import ssh_keys


@app.route('/admin/')
@admin_required
def admin_dashboard():
    servers = aws.get_instance_list(terminated=False)
    ssh_key_list = ssh_keys.list_all_ssh_keys()
    return render_template("admin.html", servers=servers, ssh_keys=ssh_key_list)


@app.route('/admin/users/<owner>')
@admin_required
def admin_server_listing_owner(owner):
    servers = aws.get_instance_list(owner=owner, terminated=False)
    ssh_key_list = ssh_keys.list_ssh_keys(owner)
    return render_template("admin.html", servers=servers, owner=owner,
                           ssh_keys=ssh_key_list)


@app.route('/admin/users/<owner>/<state>')
@admin_required
def admin_server_listing_owner_state(owner, state):
    servers = aws.get_instance_list(owner=owner, state=state)
    return render_template("admin.html", servers=servers, owner=owner)


@app.route('/admin/state/<state>')
@admin_required
def admin_server_listing_state(state):
    servers = aws.get_instance_list(state=state)
    return render_template("admin.html", servers=servers)
