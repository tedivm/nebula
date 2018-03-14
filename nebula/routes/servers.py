from flask import Flask, session, redirect, url_for, escape, request, render_template, jsonify, abort
from nebula import app
from nebula.routes.decorators import login_required, admin_required
from nebula.routes.helpers import request_wants_json
from nebula.models import profiles
from nebula.services import aws
from nebula.services import ldapuser


@app.route('/servers/launch', methods=["GET", "POST"])
@login_required
def server_launch():
    if request.method == 'POST':
        profile_id = request.form['profile']
        instancetype = request.form['instancetype']
        owner = session['username']
        size = int(request.form['size'])
        num_instances = int(request.form['num_instances'])
        group_id = aws.generate_group_id()
        label = False
        if 'label' in request.form and len(request.form['label']) > 0:
            label = request.form['label']
        shutdown = False
        if 'shutdown' in request.form and len(request.form['shutdown']) > 0:
            shutdown = request.form['shutdown']
        for _ in range(num_instances):
            aws.launch_instance.delay(group_id, profile_id, instancetype, owner, size, label, shutdown)
        return redirect(url_for('server_list'))
    profile_list = profiles.list_profiles()
    return render_template("server_form.html", profiles=profile_list)


@app.route('/servers/')
@login_required
def server_list():
    servers = aws.get_instance_list(owner=session['username'], terminated=False)
    return render_template("servers.html", servers=servers)


@app.route('/servers/<instance_id>/start', methods = ["GET", "POST"])
@login_required
def server_start(instance_id):
    if not should_allow(instance_id):
        abort(404)
    if request.method == 'POST':
        aws.start_instance.delay(instance_id)
        if request_wants_json():
            return jsonify(True)
        else:
            return redirect(url_for('server_list'))

    return render_template("confirm.html", message="")


@app.route('/servers/<instance_id>/stop', methods = ["GET", "POST"])
@login_required
def server_stop(instance_id):
    if not should_allow(instance_id):
        abort(404)
    if request.method == 'POST':
        aws.stop_instance.delay(instance_id)
        if request_wants_json():
            return jsonify(True)
        else:
            return redirect(url_for('server_list'))

    return render_template("confirm.html", message="")


@app.route('/server/<instance_id>/schedulestop', methods = ["GET", "POST"])
@login_required
def server_schedule_stop(instance_id):
    if not should_allow(instance_id):
        abort(404)
    if request.method == 'POST':
        if 'stoptime' not in request.form:
            abort(400)
        if not isinstance(request.form['stoptime'], int):
            abort(400)
        if len(request.form['stoptime']) <= 0:
            abort(400)
        stoptime = request.form['stoptime']
        aws.tag_instance.delay(instance_id, 'Shutdown', stoptime)
        if request_wants_json():
            return jsonify(True)
        else:
            return redirect(url_for('server_list'))
    return render_template("confirm.html", message="")


@app.route('/servers/<instance_id>/reboot', methods = ["GET", "POST"])
@login_required
def server_reboot(instance_id):
    if not should_allow(instance_id):
        abort(404)
    if request.method == 'POST':
        aws.reboot_instance.delay(instance_id)
        if request_wants_json():
            return jsonify(True)
        else:
            return redirect(url_for('server_list'))

    return render_template("confirm.html", message="")


@app.route('/server/<instance_id>/terminate', methods = ["GET", "POST"])
@login_required
def server_terminate(instance_id):
    if not should_allow(instance_id):
        abort(404)
    if request.method == 'POST':
        aws.terminate_instance.delay(instance_id)
        if request_wants_json():
            return jsonify(True)
        else:
            return redirect(url_for('server_list'))

    return render_template("confirm.html", message="")


@app.route('/server/<instance_id>/label', methods = ["GET", "POST"])
@login_required
def server_label(instance_id):
    if not should_allow(instance_id):
        abort(404)
    if request.method == 'POST':
        if 'label' not in request.form or len(request.form['label']) <= 0:
            abort(400)
        label = request.form['label']
        aws.tag_instance.delay(instance_id, 'Label', label)
        if request_wants_json():
            return jsonify(True)
        else:
            return redirect(url_for('server_list'))
    return render_template("confirm.html", message="")


@app.route('/server/<group_id>/terminate/group', methods=['GET', 'POST'])
@login_required
def server_terminate_group(group_id):
    """Terminate all instances in the specified instance group."""
    instances = aws.get_instances_in_group(group_id)
    instances_metadata = []

    for instance in instances:
        if not should_allow(instance.id):
            abort(404)
        instances_metadata.append({'id': instance.id,
                                   'private_ip_address': instance.private_ip_address})

    if request.method == 'POST':
        for instance in instances:
            if aws.can_terminate(instance):
                aws.terminate_instance.delay(instance.id)

        if request_wants_json():
            return jsonify(True)
        else:
            return redirect(url_for('server_list'))

    return render_template('confirm.html', termination_group_metadata=instances_metadata)


def should_allow(instance_id):
    if aws.is_owner(instance_id, session['username']):
        return True
    if ldapuser.is_admin(session['username']):
        return True
    return False