from flask import Flask, session, redirect, url_for, escape, request, render_template, jsonify
from nebula import app
from nebula.routes.decorators import login_required, admin_required
from nebula.services import aws
from nebula.models import ssh_keys


@app.route('/admin/')
@admin_required
def admin_dashboard():
    servers = aws.get_instance_list(terminated=False)
    ssh_key_list = ssh_keys.list_all_ssh_keys()
    return render_template("admin.html", servers=servers, ssh_keys=ssh_key_list)


@app.route('/admin/servers/index.json')
@admin_required
def admin_server_list_json():
    servers = aws.get_instance_list(terminated=False)
    serverlist = []
    for server in servers:
        tags = aws.get_tags_from_aws_object(server)
        serverdata = {
            'launch': server.launch_time,
            'cost': aws.get_cost(server),
            'group': tags.get('Group', False),
            'label': tags.get('Label', False),
            'instance_id': server.instance_id,
            'private_ip_address': server.private_ip_address,
            'instance_type': server.instance_type,
            'disk_space': tags.get('Disk_Space', False),
            'profile': tags.get('Profile', False),
            'status': tags.get('Status', False),
            'shutdown': tags.get('Shutdown', False),
            'name': tags.get('Name', False),
            'state': server.state['Name'],
            'user': tags.get('User', False),
            'image_id': server.image_id
        }
        serverlist.append(serverdata)
    return jsonify(serverlist)


@app.route('/admin/users/<owner>')
@admin_required
def admin_server_listing_owner(owner):
    servers = aws.get_instance_list(owner=owner, terminated=False)
    ssh_key_list = ssh_keys.list_ssh_keys(owner)
    return render_template("admin.html", servers=servers, owner=owner,
                           ssh_keys=ssh_key_list)


@app.route('/admin/users/<owner>/<state>')
@admin_required
def admin_server_listing_owner_state(owner, state):
    servers = aws.get_instance_list(owner=owner, state=state)
    return render_template("admin.html", servers=servers, owner=owner)


@app.route('/admin/state/<state>')
@admin_required
def admin_server_listing_state(state):
    servers = aws.get_instance_list(state=state)
    return render_template("admin.html", servers=servers)
