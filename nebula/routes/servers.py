from flask import Flask, session, redirect, url_for, escape, request, render_template, jsonify, abort, current_app
from nebula import app
from nebula.routes.decorators import login_required, admin_required, admin_or_owner_required
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
        if 'shutdown' in request.form and request.form['shutdown'] and int(request.form['shutdown']) > 0:
            shutdown = int(request.form['shutdown'])
        gpuidle = False
        if 'gpuIdleTime' in request.form and len(request.form['gpuIdleTime']) > 0:
            gpuidle = request.form['gpuIdleTime']

        for _ in range(num_instances):
            aws.launch_instance.delay(group_id, profile_id, instancetype, owner, size, label, shutdown, gpuidle)
        return redirect(url_for('server_list'))

    if current_app.config['aws'].get('use_launch_templates', False):
        profile_list = []
        for launch_template in aws.get_launch_templates():
            profile_list.append({
                "id": launch_template['LaunchTemplateId'],
                "name": launch_template['Tags'].get('NebulaShortName', launch_template['LaunchTemplateName'])
            })
    else:
        profile_list = [{"id":profile["id"], "name":profile["name"]} for profile in profiles.list_profiles()]

    return render_template("server_form.html", profiles=profile_list)


@app.route('/servers/')
@login_required
def server_list():
    servers = aws.get_instance_list(owner=session['username'], terminated=False)
    return render_template("servers.html", servers=servers)


@app.route('/servers/index.json')
@login_required
def server_list_json():
    servers = aws.get_instance_list(owner=session['username'], terminated=False)
    serverlist = []
    for server in servers:
        serverdata = get_server_information(server)
        serverlist.append(serverdata)
    return jsonify(serverlist)


@app.route('/servers/<instance_id>/start', methods = ["GET", "POST"])
@admin_or_owner_required
def server_start(instance_id):
    if request.method == 'POST':
        aws.start_instance.delay(instance_id)
        if request_wants_json():
            return jsonify(True)
        else:
            return redirect(url_for('server_list'))

    return render_template("confirm.html", message="")


@app.route('/servers/<instance_id>/stop', methods = ["GET", "POST"])
@admin_or_owner_required
def server_stop(instance_id):
    if request.method == 'POST':
        aws.stop_instance.delay(instance_id)
        if request_wants_json():
            return jsonify(True)
        else:
            return redirect(url_for('server_list'))

    return render_template("confirm.html", message="")


@app.route('/server/<instance_id>/schedulestop', methods = ["GET", "POST"])
@admin_or_owner_required
def server_schedule_stop(instance_id):


    if request.method == 'POST':

        if 'stoptime' not in request.form and 'gpustoptime' not in request.form:
            app.logger.info('stoptime and gpustoptime not in request')
            abort(400)

        tags = {}

        if 'stoptime' in request.form:
            if int(request.form['stoptime']) < 0:
                app.logger.info('stoptime is less than zero')
                abort(400)
            tags['Shutdown'] = request.form['stoptime']

        if 'gpustoptime' in request.form:
            if int(request.form['gpustoptime']) < 0:
                app.logger.info('gpustoptime is less than zero')
                abort(400)
            tags['GPU_Shutdown'] = request.form['gpustoptime']

        aws.multi_tag_instance.delay(instance_id, tags)

        if request_wants_json():
            return jsonify(True)
        else:
            return redirect(url_for('server_list'))
    return render_template("confirm.html", message="")


@app.route('/servers/<instance_id>/reboot', methods = ["GET", "POST"])
@admin_or_owner_required
def server_reboot(instance_id):
    if request.method == 'POST':
        aws.reboot_instance.delay(instance_id)
        if request_wants_json():
            return jsonify(True)
        else:
            return redirect(url_for('server_list'))

    return render_template("confirm.html", message="")


@app.route('/server/<instance_id>/terminate', methods = ["GET", "POST"])
@admin_or_owner_required
def server_terminate(instance_id):
    if request.method == 'POST':
        aws.terminate_instance.delay(instance_id)
        if request_wants_json():
            return jsonify(True)
        else:
            return redirect(url_for('server_list'))

    return render_template("confirm.html", message="")


@app.route('/server/<instance_id>/label', methods = ["GET", "POST"])
@admin_or_owner_required
def server_label(instance_id):
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


@app.route('/server/<instance_id>/info')
@admin_or_owner_required
def server_info(instance_id):
    instance = aws.get_instance(instance_id)
    info = get_server_information(instance)
    return jsonify(info)


@app.route('/groups/<group_id>/terminate/group', methods=['GET', 'POST'])
@login_required
def server_terminate_group(group_id):
    """Terminate all instances in the specified instance group."""
    instances = aws.get_instances_in_group(group_id)
    instances_metadata = []
    is_admin = ldapuser.is_admin(session['username'])
    for instance in instances:
        if not is_admin:
            if not aws.is_owner(instance_id, session['username']):
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


@app.route('/amis/<ami_id>/size.json')
@login_required
def ami_image_size(ami_id):
    return jsonify(aws.get_ami_root_size(ami_id))


@app.route('/profiles/<profile_id>/ami.json')
@login_required
def profile_ami(profile_id):
    if current_app.config['aws'].get('use_launch_templates', False):
        return jsonify(aws.get_ami_from_launch_template(profile_id))
    else:
        return jsonify(aws.get_ami_from_profile(profile_id))



def get_server_information(server):
    hourly_price = aws.get_instance_description(server.instance_type)['price']
    tags = aws.get_tags_from_aws_object(server)
    return {
        'ami': server.image_id,
        'launch': server.launch_time,
        'cost': aws.get_cost(server),
        'price': hourly_price,
        'group': tags.get('Group', False),
        'label': tags.get('Label', ''),
        'instance_id': server.instance_id,
        'private_ip_address': server.private_ip_address,
        'instance_type': server.instance_type,
        'disk_space': tags.get('Disk_Space', False),
        'profile': tags.get('Profile', False),
        'status': tags.get('Status', False),
        'shutdown': tags.get('Shutdown', False),
        'gpushutdown': tags.get('GPU_Shutdown', False),
        'name': tags.get('Name', ''),
        'state': server.state['Name']
    }
