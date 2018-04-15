import json
from nebula import app
from functools import wraps
from nebula.models import profiles
from nebula.services import export, ldapuser
from flask import request, abort, jsonify, Response


def ldap_credentials_required(f):
    """Require username and password fields to be sent in https header."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'username' not in request.headers or 'password' not in request.headers:
            return abort(401)
        if not ldapuser.authenticate(request.headers['username'], request.headers['password']):
            return abort(403)
        if not ldapuser.is_api_authorized(request.headers['username']):
            return abort(403)
        return f(*args, **kwargs)
    return decorated


@app.route('/api/profiles', methods=['GET'])
@ldap_credentials_required
def api_profiles_index():
    """Handle GET and POST profile requests."""
    if request.method == 'GET':
        # Return a list of profiles currently in the db
        return jsonify(profiles.list_profiles())


@app.route('/api/profiles', methods=['POST'])
@ldap_credentials_required
def api_profiles_create():
    if request.method == 'POST':
        profile = request.get_json()
        name = profile.get('name', '')
        ami = profile.get('ami', '')
        userdata = profile.get('userdata', '')
        profile_id = profiles.create_profile(name, ami, userdata)
        return jsonify({'status': 'ok', 'id': profile_id})


@app.route('/api/profiles/<profile_id>', methods=['PUT'])
@ldap_credentials_required
def api_profiles_update(profile_id):
    """Update or delete specified profile id."""
    if request.method == 'PUT':
        existing_profile = profiles.get_profile(profile_id)
        # Update existing profile with new profile object.
        if not existing_profile:
            # Profile does not exist
            return abort(404)

        profile = request.get_json()
        name = profile.get('name', existing_profile['name'])
        ami = profile.get('ami', existing_profile['ami'])
        userdata = profile.get('userdata', existing_profile['userdata'])
        profiles.update_profile(profile_id, name, ami, userdata)
        return jsonify({'status': 'ok', 'id': profile_id})


@app.route('/api/profiles/<profile_id>', methods=['DELETE'])
@ldap_credentials_required
def api_profiles_delete(profile_id):
    if request.method == 'DELETE':
        # Remove profile stored at specified id.
        if not profiles.get_profile(profile_id):
            # Profile does not exist
            return abort(404)
        profiles.remove_profile(profile_id)
        return jsonify({'status': 'ok'})


@app.route('/api/sshkeys')
@ldap_credentials_required
def api_sshkeys_list():
    """Export ssh keys into a downloadable json file."""
    return jsonify(export.collect_all_keys())
