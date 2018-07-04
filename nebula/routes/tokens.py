from flask import url_for, render_template, jsonify, request
from nebula import app
from nebula.models import tokens
from nebula.routes.decorators import admin_required
from nebula.routes.helpers import request_wants_json


@app.route('/tokens', methods = ["GET", "POST"])
@admin_required
def token_list():
    return render_template("tokens.html", tokens=tokens.list_tokens())


@app.route('/tokens/create', methods = ["GET", "POST"])
@admin_required
def token_create():
    if request.method == 'POST':
        is_instance_token_string = request.form.get('instance_token', 'false')
        instance_token = is_instance_token_string == 'true'
        token_id, token = tokens.create_token(instance_token)
        return render_template(
            "token_creation.html",
            token_id=token_id,
            token=token,
            instance_token=instance_token
        )
    return render_template("token_form.html")


@app.route('/tokens/<token_id>/delete', methods = ["GET", "POST"])
@admin_required
def token_delete(token_id):
    if request.method == 'POST':
        tokens.remove_token(token_id)
        if request_wants_json():
            return jsonify(True)
    return redirect(url_for('token_list'))
