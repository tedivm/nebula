from passlib.context import CryptContext
from nebula.models import db
import uuid

pwd_context = CryptContext(
        schemes=["pbkdf2_sha512"],
        default="pbkdf2_sha512",
        pbkdf2_sha512__default_rounds=100000
)


def create_token(creator, instance_token=False):
    # Create random number for ID
    token_id = str(uuid.uuid4())[-12:]

    # Generate a UUID
    token = str(uuid.uuid4())

    # Hash it- don't store the token
    token_hash = pwd_context.hash(token)

    query = "INSERT INTO tokens(token_id, creator, token_hash, instance_token) VALUES(%s, %s, %s, %s) RETURNING id"
    db.insert_and_get_id(query, (token_id, creator, token_hash, instance_token))

    return (token_id, token)


def verify(token_id, token):
    query = "SELECT * FROM tokens WHERE token_id = %s"
    token_data = db.find_one_dict(query, (token_id,))
    if not token_data:
        return False
    if pwd_context.verify(token, token_data['token_hash']):
        query = "UPDATE tokens SET last_used = now() WHERE token_id = %s"
        db.execute(query, (token_id,))
        return True

    return False


def is_instance(token_id):
    token_data = get_token(token_id)
    return token_data['instance_token']


def get_token(token_id):
    query = "SELECT * FROM tokens WHERE token_id = %s"
    return db.find_one_dict(query, (token_id,))


def remove_token(token_id):
    query = "DELETE FROM tokens WHERE token_id = %s"
    db.execute(query, (token_id,))


def list_tokens():
    query = "SELECT * FROM tokens ORDER BY token_id ASC"
    return db.find_all_dict(query)
