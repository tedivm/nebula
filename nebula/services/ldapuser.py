from flask import Flask, g
from nebula import app
from nebula.services.cache import cache
from ldap3 import Server, Connection, ALL


@cache.cache(expires=600)
def is_admin(user):
    if user_in_group(user, app.config['LDAP_BANNED_GROUP']):
        return False
    return user_in_group(user, app.config['LDAP_ADMIN_GROUP'])


@cache.cache(expires=600)
def is_valid_user(user):
    # Banned users are not allowed. Obviously.
    if 'LDAP_BANNED_GROUP' in app.config:
        if user_in_group(user, app.config['LDAP_BANNED_GROUP']):
            return False

    # Regular users also allowed.
    if user_in_group(user, app.config['LDAP_USER_GROUP']):
        return True

    # Lets not ban admins who are not in the user group.
    if is_admin(user):
        return True

    return False


@cache.cache(expires=60)
def user_in_group(user, group):
    conn = get_bound_connection()
    group_search = get_dn_from_group(group)
    group_object = '(objectclass=%s)' % (app.config['LDAP_GROUP_OBJECT'],)
    conn.search(group_search, group_object, attributes=['memberUid'])
    if len(conn.entries) < 1:
        return False
    members = conn.entries[0].memberUid
    return user in members


def get_bound_connection():
    if 'ldap_connection' in g:
        return g.ldap_connection
    server = Server(app.config['LDAP_PROVIDER_URL'], get_info=ALL)  # define an unsecure LDAP server, requesting info on DSE and schema
    g.ldap_connection = Connection(server, app.config['LDAP_BIND_DN'], app.config['LDAP_BIND_PASSWORD'], auto_bind=True)
    return g.ldap_connection


def authenticate(user, password):
    # define the server
    s = Server(app.config['LDAP_PROVIDER_URL'], get_info=ALL)  # define an unsecure LDAP server, requesting info on DSE and schema

    # define the connection
    user_dn = get_dn_from_user(user)
    c = Connection(app.config['LDAP_PROVIDER_URL'], user=user_dn, password=password)

    # perform the Bind operation - used to check user password.
    if not c.bind():
        return False

    # check to see if user is actually a valid user.
    return is_valid_user(user)


def get_dn_from_user(user):
    return "%s=%s,%s" % (app.config['LDAP_USERNAME_ATTRIBUTE'], user, app.config['LDAP_USER_BASE'] )


def get_dn_from_group(group):
    return 'cn=%s,%s' % (group, app.config['LDAP_GROUP_BASE'])
