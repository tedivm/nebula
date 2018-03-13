import boto3
from botocore.exceptions import ClientError
import requests
from flask import current_app,g
from nebula import app,celery
from nebula.services.cache import cache
from nebula.models import profiles
import math
import pytz
from datetime import datetime
import uuid


# Remove legacy instance types to keep clutter down and prevent people from
# using inefficiently priced machines.
filter_families = [

    # High Density Storage
    'i2',
    'd2',

    # Legacy Machines
    'c1',
    'c2',
    'c3',
    'cc1',
    'cc2',
    'cg1',
    'cr1',
    'hi1',
    'hs1',
    'm1',
    'm2',
    'm3',
    'r3',
    't1',
]


def is_running(instance):
    return instance.state['Name'] == 'running'


def can_start(instance):
    return instance.state['Name'] == 'stopped'


def can_stop(instance):
    if instance.state['Name'] == 'stopped':
        return False
    if instance.state['Name'] == 'terminated':
        return False
    if instance.state['Name'] == 'stopping':
        return False
    return True


def can_restart(instance):
    return instance.state['Name'] == 'running'


def can_terminate(instance):
    return instance.state['Name'] != 'terminated'


def can_resize(instance):
    return instance.state['Name'] == 'stopped'


def seconds_billed(instance):
    if instance.state['Name'] != 'running':
        return 0

    now = datetime.now(pytz.utc).timestamp()
    launch = instance.launch_time.timestamp()
    seconds = now - launch
    if seconds < 60:
        return 60
    return seconds


def get_ec2_client():
    with app.app_context():
        conn = getattr(g, '_ec2', None)
        if conn is None:
            g._ec2 = boto3.resource('ec2', region_name=current_app.config['REGION_NAME'])
        return g._ec2


def generate_group_id():
    """Generate a random UUID hex string to group launched instances."""
    return uuid.uuid4().hex


@celery.task(rate_limit='20/m', expires=300, acks_late=False)
def launch_instance(group_id, profile_id, instancetype, owner, size=120, label = False, shutdown = False):

    with app.app_context():
        # within this block, current_app points to app.
        profile = profiles.get_profile(profile_id)
        print('Launching %s for %s with profile "%s"' % (instancetype, owner, profile))
        userdata = profile['userdata']
        ImageID = profile['ami']

        startArgs = {
            'DryRun': False,
            'ImageId': ImageID,
            'MinCount': 1,
            'MaxCount': 1,
            'UserData': userdata,
            'InstanceType': instancetype,
            'Monitoring': {
                'Enabled': True
            },
            'DisableApiTermination': False,
            'InstanceInitiatedShutdownBehavior': 'stop',
            'EbsOptimized': app.config.get('EBS_OPTIMIZED', False),
            'BlockDeviceMappings': [
                {
                    'DeviceName': '/dev/sda1',
                    'Ebs': {
                        'VolumeSize': size,
                        'VolumeType': 'gp2'
                    }
                }
            ]
        }

        if 'SUBNET_ID' not in current_app.config:
            raise ValueError("SUBNET_ID must be saved in configuration")
        if ',' in current_app.config['SUBNET_ID']:
            subnets = current_app.config['SUBNET_ID'].split(',')
        else:
            subnets = [current_app.config['SUBNET_ID']]

        if 'SECURITY_GROUP_ID' in current_app.config:
            startArgs['SecurityGroupIds'] = [current_app.config['SECURITY_GROUP_ID']]

        if 'IAM_INSTANCE_PROFILE' in current_app.config:
            startArgs['IamInstanceProfile'] = {
                'Arn': current_app.config['IAM_INSTANCE_PROFILE']
            }

        ec2 = get_ec2_client()

        # Attempt on all available subnets
        while True:
            startArgs['SubnetId'] = subnets.pop(0)
            try:
                instances = ec2.create_instances(**startArgs)
                break
            except ClientError as e:
                if len(subnets) < 1:
                    raise e

        # Wait for all machine requests to process so we can tag them.
        while True:
            launched = True
            for instance in instances:
                if instance.state == 16:
                    launched = False
            if launched:
                break
            time.sleep(5)

        for instance in instances:
            print('Cluster start - tag')
            tags = [
                { 'Key': 'nebula', 'Value': 'true' },
                { 'Key': 'User', 'Value': owner },
                { 'Key': 'Profile', 'Value': profile['name'] },
                { 'Key': 'Group', 'Value': group_id },
                { 'Key': 'Disk_Space', 'Value': str(size) }
            ]
            if label:
                tags.append({ 'Key': 'Label', 'Value': label })
            if shutdown:
                tags.append({ 'Key': 'Shutdown', 'Value': shutdown })
            instance.create_tags(Tags=tags)

        return True


@celery.task(rate_limit='20/m', expires=3600)
def stop_instance(instance_id):
    print('Stopping instance %s' % (instance_id,))
    ec2 = get_ec2_client()
    ec2.instances.filter(InstanceIds=[instance_id]).stop()
    tag_instance(instance_id, 'Shutdown', 'false')


@celery.task(rate_limit='20/m', expires=300)
def start_instance(instance_id):
    print('Starting instance %s' % (instance_id,))
    ec2 = get_ec2_client()
    ec2.instances.filter(InstanceIds=[instance_id]).start()
    tag_instance(instance_id, 'Shutdown', 'false')

@celery.task(rate_limit='20/m', expires=300)
def reboot_instance(instance_id):
    print('Rebooting instance %s' % (instance_id,))
    ec2 = get_ec2_client()
    ec2.instances.filter(InstanceIds=[instance_id]).reboot()


@celery.task(rate_limit='20/m')
def terminate_instance(instance_id):
    print('Terminating instance %s' % (instance_id,))
    ec2 = get_ec2_client()
    ec2.instances.filter(InstanceIds=[instance_id]).terminate()

@celery.task(rate_limit='20/m')
def tag_instance(instance_id, tag, value):
    ec2 = get_ec2_client()
    ec2.instances.filter(InstanceIds=[instance_id]).create_tags(
        Tags=[
            { 'Key': tag, 'Value': value }
        ]
    )

@cache.cache()
def is_owner(instance_id, user):
    ec2 = get_ec2_client()
    print(instance_id)
    instances = ec2.instances.filter(InstanceIds=[instance_id])
    for instance in instances:
        tags = get_tags_from_aws_object(instance)
        return 'User' in tags and tags['User'] == user
    return False


def get_tags_from_aws_object(ec2_object):
    tag_dict = {}
    if ec2_object.tags is None:
        return tag_dict
    for tag in ec2_object.tags:
        tag_dict[tag['Key']] = tag['Value']
    return tag_dict


def get_instance_list(owner=None, state=False, terminated=True, update_volumes=False):
    ec2 = get_ec2_client()
    filters = [{'Name':'tag:nebula', 'Values':['true']}]

    if state:
        if isinstance(state, list):
            states = state
        else:
            states = [state]
        filters.append({'Name':'instance-state-name', 'Values':states})

    if owner:
        filters.append({'Name':'tag:User', 'Values':[owner]})
    if not terminated:
        states = ['pending', 'running', 'shutting-down', 'stopping', 'stopped', 'rebooting']
        filters.append({'Name':'instance-state-name', 'Values':states})

    # Use optional arg if attached EBS volumes need to be updated when retrieved
    if update_volumes:
        instances = ec2.instances.filter(Filters=filters)
        for instance in instances:
            total_volume_capacity = 0
            # Create collection of all attached EBS volumes
            volumes = instance.volumes.all()
            for volume in volumes:
                total_volume_capacity += volume.size  # GiBs

            instance.create_tags(Tags=[
                { 'Key': 'Disk_Space', 'Value': str(total_volume_capacity) }
            ])

    return ec2.instances.filter(Filters=filters)


def get_instances_in_group(group_id):
    """Return a list of instances belonging to the specified group ID."""
    ec2 = get_ec2_client()
    filters = [{ 'Name': 'tag:Group', 'Values': [group_id] }]
    instances = ec2.instances.filter(Filters=filters)
    return list(instances)


#@cache.cache()
def get_instance_types():
    data = get_instance_descriptions()
    instance_types = list(data.keys())

    filtered = []

    for instance_type in instance_types:
        instance_family = instance_type.split('.')[0]
        if instance_family not in filter_families:
            filtered.append(instance_type)

    filtered.sort()
    return filtered


def get_instance_description(instance_type):
    descriptions = get_instance_descriptions()
    if instance_type in descriptions:
        return descriptions[instance_type]
    return False


@cache.cache()
def get_instance_descriptions():
    r = requests.get('https://tedivm.github.io/ec2details/api/ec2instances.json')
    return r.json()
