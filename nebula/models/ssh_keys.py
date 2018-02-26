from nebula import app
from nebula.models import db


def create_new_key(username, key_name, ssh_key):
    """Create a new SSH key entry in the database."""
    query = 'INSERT INTO ssh_keys(username, key_name, ssh_key) VALUES(%s, %s, %s) RETURNING id;'
    return db.insert_and_get_id(query, (username, key_name, ssh_key))


def list_ssh_keys(username):
    """Return all SSH keys created by a specific user."""
    query = 'SELECT * FROM ssh_keys WHERE username = %s;'
    return db.find_all_dict(query, (username,))


def list_all_ssh_keys():
    """Return all SSH keys in the database."""
    query = 'SELECT * FROM ssh_keys'
    return db.find_all_dict(query)


def get_ssh_key(id):
    """Retrieve one ssh key listing specified by id."""
    query = 'SELECT * FROM ssh_keys WHERE id = %s'
    return db.find_one_dict(query, (id,))


def update_ssh_key(id, username, key_name, ssh_key):
    """Update the ssh key listing specified by the id."""
    query = 'UPDATE ssh_keys SET username = %s, key_name = %s, ssh_key = %s WHERE id = %s'
    db.execute(query, (username, key_name, ssh_key, id))


def remove_ssh_key(id):
    """Delete the ssh key listing specified by the id."""
    query = 'DELETE FROM ssh_keys WHERE id = %s'
    db.execute(query, (id,))


def get_owner(id):
    """Retrieve the username that owns the specified ssh key id."""
    query = 'SELECT username FROM ssh_keys WHERE id = %s'
    return db.find_one_dict(query, (id,))['username']
