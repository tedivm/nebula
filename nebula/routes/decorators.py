import datetime
import time
from functools import wraps
from flask import g, request, redirect, url_for, session, make_response
from wsgiref.handlers import format_date_time
from nebula.services import ldapuser
from nebula.models import ssh_keys
from nebula.routes import errors


def is_logged_in():
    """Check if user is logged in."""
    if 'username' not in session:
        return False

    if not ldapuser.is_valid_user(session['username']):
        session.delete()
        return False

    return True


def login_required(f):
    @wraps(f)
    def decorated_login_function(*args, **kwargs):
        if not is_logged_in():
            return redirect(url_for('login'))

        return f(*args, **kwargs)
    return decorated_login_function


def admin_required(f):
    @wraps(f)
    def decorated_admin_function(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('login'))

        if not ldapuser.is_admin(session['username']):
            return False

        return f(*args, **kwargs)
    return decorated_admin_function


def admin_or_belongs_to_user(f):
    """Decorator that ensures user is admin or owner of ssh key."""
    @wraps(f)
    def func(*args, **kwargs):
        if not is_logged_in():
            return redirect(url_for('login'))

        current_user = session['username']
        ssh_key_id = kwargs.get('ssh_key_id')
        owner = ssh_keys.get_owner(ssh_key_id)
        if current_user != owner and not ldapuser.is_admin(current_user):
            return errors.show_error(401, 'Unauthorized')

        return f(*args, **kwargs)
    return func


def httpresponse(expires=None, round_to_minute=False, content_type='text/html'):
    def cache_decorator(view):
        @wraps(view)
        def cache_func(*args, **kwargs):
            now = datetime.datetime.now()

            response = make_response(view(*args, **kwargs))
            response.headers['Content-Type'] = content_type
            response.headers['Last-Modified'] = format_date_time(time.mktime(now.timetuple()))

            if expires is None:
                response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
                response.headers['Expires'] = '-1'
            else:
                expires_time = now + datetime.timedelta(seconds=expires)

                if round_to_minute:
                    expires_time = expires_time.replace(second=0, microsecond=0)

                response.headers['Cache-Control'] = 'public'
                response.headers['Expires'] = format_date_time(time.mktime(expires_time.timetuple()))

            return response
        return cache_func
    return cache_decorator
