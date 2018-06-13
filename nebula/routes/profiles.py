from flask import Flask, session, redirect, url_for, escape, request, render_template, jsonify
from nebula import app
from nebula.routes.decorators import login_required, admin_required
from nebula.routes.helpers import request_wants_json
from nebula.models import profiles

@app.route('/profiles/create', methods = ["GET", "POST"])
@admin_required
def profiles_create():
    if request.method == 'POST':
        name = request.form['name']
        ami = request.form.get('ami', None)
        owner = request.form.get('owner', None)
        filter = request.form.get('filter', None)
        userdata = request.form.get('userdata', None)
        profiles.create_profile(name, ami, owner, filter, userdata)
        return redirect(url_for('profiles_list'))
    return render_template("profile_form.html", profile={})


@app.route('/profiles/<profile_id>/update', methods = ["GET", "POST"])
@admin_required
def profiles_update(profile_id):
    profile = profiles.get_profile(profile_id)
    print(profile)
    if request.method == 'POST':
        name = request.form.get('name', profile['name'])
        ami = request.form.get('ami', profile['ami'])
        owner = request.form.get('owner', profile['owner'])
        filter = request.form.get('filter', profile['filter'])
        userdata = request.form.get('userdata', None)
        profiles.update_profile(profile_id, name, ami, owner, filter, userdata)
        return redirect(url_for('profiles_list'))
    return render_template("profile_form.html", profile=profile)


@app.route('/profiles/<profile_id>/remove', methods = ["GET", "POST"])
@admin_required
def profiles_remove(profile_id):
    if request.method == 'POST':
        profiles.remove_profile(profile_id)
        if request_wants_json():
            return jsonify(True)
        else:
            return redirect(url_for('profiles_list'))
    return render_template("confirm.html")


@app.route('/profiles/list')
@admin_required
def profiles_list():
    profile_list = profiles.list_profiles()
    return render_template("profiles.html", profiles=profile_list)
