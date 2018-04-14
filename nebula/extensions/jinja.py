from flask import g, request, redirect, url_for, session, make_response
from nebula import app
from nebula.services import ldapuser, aws, notifications

app.jinja_env.globals.update(site_title=app.config['general'].get('site_title', 'nebula'))

def isloggedin():
    return 'username' in session

def isadmin():
    try:
        if 'username' in session:
            return ldapuser.is_admin(session['username'])
    except:
        # Since this is a template function it should not propagate the error
        # up, as it is called on the error pages as well.
        return False
    return False


app.jinja_env.globals.update(isloggedin=isloggedin)
app.jinja_env.globals.update(isadmin=isadmin)


instance_types = aws.get_instance_types()
app.jinja_env.globals.update(instance_types=instance_types)
app.jinja_env.globals.update(get_instance_description=aws.get_instance_description)
app.jinja_env.globals.update(get_tags_from_aws_object=aws.get_tags_from_aws_object)
app.jinja_env.globals.update(get_updated_prices=aws.get_updated_prices)
app.jinja_env.globals.update(as_currency=notifications.as_currency)

app.jinja_env.globals.update(instance_can_start=aws.can_start)
app.jinja_env.globals.update(instance_can_stop=aws.can_stop)
app.jinja_env.globals.update(instance_can_restart=aws.can_restart)
app.jinja_env.globals.update(instance_can_terminate=aws.can_terminate)
app.jinja_env.globals.update(instance_can_resize=aws.can_resize)
app.jinja_env.globals.update(instance_seconds_billed=aws.seconds_billed)
app.jinja_env.globals.update(instance_is_running=aws.is_running)


import pytz
from pytz import timezone
import tzlocal

def datetimefilter(value, format="%Y-%m-%d %H:%M"):
    tz = pytz.timezone('America/Los_Angeles') # timezone you want to convert to from UTC
    local_dt = value.astimezone(tz)
    return local_dt.strftime(format)

app.jinja_env.filters['datetimefilter'] = datetimefilter
