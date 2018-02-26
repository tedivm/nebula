import json
from nebula import app
from functools import wraps
from nebula.models import profiles
from nebula.services import ldapuser
from flask import request, abort, jsonify, Response


def ldap_credentials_required(f):
    """Require username and password fields to be sent in https header."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'username' not in request.headers or 'password' not in request.headers:
            return abort(401)
        elif not ldapuser.authenticate(request.headers['username'],
                                       request.headers['password']):
            return abort(401)
        return f(*args, **kwargs)
    return decorated


@app.route('/api/profiles', methods=['GET', 'POST'])
@ldap_credentials_required
def profiles_api():
    """Handle GET and POST profile requests."""
    if request.method == 'GET':
        # Return a list of profiles currently in the db
        return jsonify(profiles.list_profiles())

    if request.method == 'POST':
        # Accept new profile in json: {"name": "x", "ami": "y", "userdata": "z"}
        profile = request.get_json()

        name = profile.get('name', '')
        ami = profile.get('ami', '')
        userdata = profile.get('userdata', '')

        profiles.create_profile(name, ami, userdata)

        return Response('Profile created. name: %s, ami: %s, userdata: %s' %
                        (name, ami, userdata))


@app.route('/api/profiles/<profile_id>', methods=['PUT', 'DELETE'])
@ldap_credentials_required
def update_or_delete_profile(profile_id):
    """Update or delete specified profile id."""
    if request.method == 'PUT':
        # Update existing profile with new profile object.
        if not profiles.get_profile(profile_id):
            # Profile does not exist
            return abort(404)

        profile = request.get_json()

        name = profile.get('name', '')
        ami = profile.get('ami', '')
        userdata = profile.get('userdata', '')

        profiles.update_profile(profile_id, name, ami, userdata)

        return Response('Profile %s updated. name: %s, ami %s, userdata: %s' %
                        (profile_id, name, ami, userdata))

    if request.method == 'DELETE':
        # Remove profile stored at specified id.
        if not profiles.get_profile(profile_id):
            # Profile does not exist
            return abort(404)

        profiles.remove_profile(profile_id)

        return Response('Profile %s deleted.' % profile_id)
