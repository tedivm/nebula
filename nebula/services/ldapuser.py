from flask import Flask, g
from nebula import app
from nebula.services.cache import cache
from ldap3 import Server, Connection, ALL


def is_admin(user):
    if user_in_group(user, app.config['ldap']['banned_group']):
        return False
    return user_in_group(user, app.config['ldap']['admin_group'])


def is_valid_user(user):
    # Banned users are not allowed. Obviously.
    if 'banned_group' in app.config['ldap']:
        if user_in_group(user, app.config['ldap']['banned_group']):
            return False

    # Regular users also allowed.
    if user_in_group(user, app.config['ldap']['user_group']):
        return True

    # Lets not ban admins who are not in the user group.
    if is_admin(user):
        return True

    return False


# Cache for two seconds to prevent overloading the ldap server.
@cache.cache(expires=2)
def user_in_group(user, group):
    conn = get_bound_connection()
    group_search = get_dn_from_group(group)
    group_object = '(objectclass=%s)' % (app.config['ldap']['group_object_class'],)
    conn.search(group_search, group_object, attributes=['memberUid'])
    if len(conn.entries) < 1:
        return False
    members = conn.entries[0].memberUid
    return user in members


def get_bound_connection():
    if 'ldap_connection' in g:
        return g.ldap_connection
    server = Server(app.config['ldap']['host'], get_info=ALL)  # define an unsecure LDAP server, requesting info on DSE and schema
    g.ldap_connection = Connection(server, app.config['ldap']['bind_dn'], app.config['ldap']['bind_password'], auto_bind=True)
    return g.ldap_connection


def authenticate(user, password):
    # define the server
    s = Server(app.config['ldap']['host'], get_info=ALL)  # define an unsecure LDAP server, requesting info on DSE and schema

    # define the connection
    user_dn = get_dn_from_user(user)
    c = Connection(app.config['ldap']['host'], user=user_dn, password=password)

    # perform the Bind operation - used to check user password.
    if not c.bind():
        print('Unable to bind user %s' % (user_dn))
        return False

    print('Checking to see if user %s is valid' % (user_dn))
    # check to see if user is actually a valid user.
    return is_valid_user(user)


def get_dn_from_user(user):
    return "%s=%s,%s" % (app.config['ldap']['username_attribute'], user, app.config['ldap']['user_base'] )


def get_dn_from_group(group):
    return '%s=%s,%s' % (app.config['ldap']['group_attribute'], group, app.config['ldap']['group_base'])
