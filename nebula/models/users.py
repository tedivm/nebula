from nebula.models import db

def get_user_token(user):
    query = "SELECT * FROM users WHERE username = %s"
    result = db.find_one_dict(query, (user,))
    if not result:
        return False
    return result['security_token']

def save_user_token(user, token):
    query = '''INSERT INTO users (username, security_token) VALUES (%s, %s)
        ON CONFLICT (username) DO UPDATE
        SET security_token = %s;'''
    db.execute(query, (user, token, token))
