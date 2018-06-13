from nebula import app
from nebula.models import db
from nebula.services.cache import cache


def create_profile(name, ami=None, owner=None, filter=None, userdata=None):
    query = "INSERT INTO profiles(name, ami, owner, filter, userdata) VALUES(%s, %s, %s, %s, %s) RETURNING id"
    return db.insert_and_get_id(query, (name, ami, owner, filter, userdata))


def update_profile(id, name, ami=None, owner=None, filter=None, userdata=None):
    query = "UPDATE profiles SET name = %s, ami = %s, owner = %s, filter = %s, userdata = %s WHERE id = %s"
    db.execute(query, (name, ami, owner, filter, userdata, id))


def remove_profile(id):
    query = "DELETE FROM profiles WHERE id = %s"
    db.execute(query, (id,))


def get_profile(id):
    query = "SELECT * FROM profiles WHERE id = %s"
    return db.find_one_dict(query, (id,))


def list_profiles():
    query = "SELECT * FROM profiles ORDER BY name ASC"
    return db.find_all_dict(query)
