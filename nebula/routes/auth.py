from flask import Flask, session, redirect, url_for, escape, request, render_template
from nebula import app

from nebula.services import ldapuser


@app.route('/logout', methods = ["GET", "POST"])
def logout():
    # remove the username from the session if it's there
    session.pop('username', None)
    session.pop('my_id', None)
    return redirect(url_for('index'))


@app.route('/login/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if ldapuser.authenticate(username, password):
            session['username'] = username
            return redirect(url_for('index'))
    return render_template("login.html")
