from flask import Flask, session, redirect, url_for, escape, request, render_template
from nebula import app
from nebula.models import users
from nebula.services import ldapuser
import pyotp
import time


@app.route('/logout', methods = ["GET", "POST"])
def logout():
    # Invalidate the entire session.
    session.clear()
    return redirect(url_for('index'))


@app.route('/login/', methods=['GET', 'POST'])
def login():
    # Redirect to index if already logged in.
    if request.method == 'GET':
        if 'username' in session:
            return redirect(url_for('index'))

    # Authenticate user
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if ldapuser.authenticate(username, password):
            session['partial_authentication'] = username
            session['partial_authentication_time'] = time.time()
            token = users.get_user_token(username)
            if token:
                return redirect(url_for('login_2fa'))
            else:
                # App requires 2FA but it isn't setup for this user.
                # Redirect to the 2FA setup page to complete authentication.
                if 'require_2fa' in app.config['general']:
                    if app.config['general']['require_2fa']:
                        return redirect(url_for('user_2fa'))

                # 2FA isn't required and the user has logged in successfully.
                session.clear()
                session['username'] = username
                return redirect(url_for('index'))

    # Send login form to user.
    return render_template("login.html")

@app.route('/login/2fa', methods=['GET', 'POST'])
def login_2fa():
    if 'partial_authentication' not in session:
        return redirect(url_for('login'))

    username = session['partial_authentication']
    saved_token = users.get_user_token(username)

    # It should not be possible to get to this page without a saved token.
    if not saved_token:
        return redirect(url_for('login'))

    if request.method == 'POST':
        passed_token = request.form.get('token', False)
        totp = pyotp.TOTP(saved_token)
        if passed_token and totp.verify(passed_token):
            session['username'] = username
            session.pop('partial_authentication', None)
            return redirect(url_for('index'))

    return render_template("login_2fa.html")

@app.route('/user/2fa', methods=['GET', 'POST'])
def user_2fa():

    # Only allow partial authentication to last for two minutes.
    if 'partial_authentication_time' in session:
        if (time.time() - session['partial_authentication_time']) > 120:
            session.clear()
            return redirect(url_for('login'))

    if 'partial_authentication' in session:
        # Only users without a 2fa code can add them during login.
        username = session['partial_authentication']
        saved_token = users.get_user_token(username)
        if saved_token:
            session.clear()
            return redirect(url_for('login'))
    elif 'username' in session:
        username = session['username']
    else:
        # Session has no authentication variables- redirect to login.
        session.clear()
        return redirect(url_for('login'))

    # Save a new 2fa_token in the session.
    if not '2fa_token' in session:
        session['2fa_token'] = pyotp.random_base32()

    # Build new TOTP URI to send to front end for QR Code generation
    new_totp = pyotp.totp.TOTP(session['2fa_token'])
    site = app.config['general']['site_name']
    provisioning_uri = new_totp.provisioning_uri(username, issuer_name=site)

    # Get old token if it exists.
    saved_token = users.get_user_token(username)
    if saved_token:
        has_token = True
    else:
        has_token = False

    # Only allow 2fa authentication to last for five minutes.
    if '2fa_validated' in session:
        if (time.time() - session['2fa_validated']) > 300:
            session.pop('2fa_validated')


    if request.method == 'POST':

        # If user has 2FA enabled they need to validate against existing secret.
        if has_token:
            if '2fa_validated' not in session or not session['2fa_validated']:
                old_totp = pyotp.TOTP(saved_token)
                old_token = request.form.get('token', False)
                if not old_token or not old_totp.verify(old_token):
                    return render_template("login_2fa.html")

                # Record validation time so it can be allowed to expire.
                session['2fa_validated'] = time.time()

                return render_template("user_2fa.html",
                                       provisioning_uri=provisioning_uri)


        new_token = request.form.get('new_token', False)
        if not new_token or not new_totp.verify(new_token):
            return render_template("user_2fa.html",
                                   provisioning_uri=provisioning_uri,
                                   newfail=True)

        # User has verified the token
        users.save_user_token(username, session['2fa_token'])

        # Complete authentication if not already finished.
        if 'partial_authentication' in session:
            session.clear()
            session['username'] = username

        if '2fa_token' in session:
            session.pop('2fa_token')
        if '2fa_validated' in session:
            session.pop('2fa_validated')

        # Redirect to home- change this when a user page is built.
        return redirect(url_for('index'))

    # If user has a token it must be validated before a new one can be set.
    if has_token:
        if not '2fa_validated' in session or not session['2fa_validated']:
            return render_template("login_2fa.html")

    return render_template("user_2fa.html", provisioning_uri=provisioning_uri)
