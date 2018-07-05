import boto3
from botocore.exceptions import ClientError
from dateutil import parser
import json
import requests
from flask import current_app,g
from nebula import app,celery
from nebula.services.cache import cache
from nebula.models import profiles
import math
import pytz
from datetime import datetime
import time
import uuid
import yaml


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


def get_cost(instance):
    seconds = seconds_billed(instance)
    if seconds < 1:
        return 0
    prices = get_updated_prices()
    cost = round(((prices[instance.instance_type] / 3600) * seconds), 2)
    if cost < 0.01:
        cost = 0.01
    return cost


@cache.cache()
def get_updated_prices():
    region = app.config['aws']['region']
    prices = {}
    instance_data = get_instance_descriptions()
    for instance_type, data in instance_data.items():
        if region in data['prices']['Linux']:
            prices[instance_type] = data['prices']['Linux'][region]['Shared']
    return prices


@cache.cache()
def get_ami_root_size(ami):
    client = get_ec2_client()
    image = client.Image(ami)
    if not image:
        return False
    for device in image.block_device_mappings:
        if device['DeviceName'] == image.root_device_name:
            if 'Ebs' in device and 'VolumeSize' in device['Ebs']:
                return device['Ebs']['VolumeSize']
    return False


def get_ec2_client():
    with app.app_context():
        conn = getattr(g, '_ec2', None)
        if conn is None:
            g._ec2 = boto3.resource('ec2', region_name=current_app.config['aws']['region'])
        return g._ec2


def generate_group_id():
    """Generate a random UUID hex string to group launched instances."""
    return uuid.uuid4().hex


@cache.cache(expire=60)
def get_ami_from_profile(profile_id):
    with app.app_context():
        profile = profiles.get_profile(profile_id)

        if 'ami' in profile and profile['ami']:
            return profile['ami']

        client = boto3.client('ec2', region_name=current_app.config['aws']['region'])
        filters = yaml.load(profile['filter'])
        if 'owner' in profile:
            response = client.describe_images(Owners=[profile['owner']], Filters=filters)
        else:
            response = client.describe_images(Filters=filters)

        if 'Images' not in response:
            raise LookupError('Unable to find AMI with required filters')

        response['Images']
        latest = None
        for image in response['Images']:
            if not latest:
                latest = image
                continue
            if parser.parse(image['CreationDate']) > parser.parse(latest['CreationDate']):
                latest = image
        return latest['ImageId']


@celery.task(rate_limit='20/m', expires=300, acks_late=False)
def launch_instance(group_id, profile_id, instancetype, owner, size=120, label = False, shutdown = False):

    with app.app_context():
        # within this block, current_app points to app.
        profile = profiles.get_profile(profile_id)
        print('Launching %s for %s with profile "%s"' % (instancetype, owner, profile))
        userdata = profile['userdata']
        ImageID = get_ami_from_profile(profile_id)

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
            'EbsOptimized': app.config['aws'].get('ebs_optimized', False),
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

        if 'subnets' not in current_app.config['aws']:
            raise ValueError("SUBNET_ID must be saved in configuration")

        if 'security_group' in current_app.config['aws']:
            startArgs['SecurityGroupIds'] = [current_app.config['aws']['security_group']]

        if 'iam_instance_profile' in current_app.config['aws']:
            startArgs['IamInstanceProfile'] = {
                'Arn': current_app.config['aws']['iam_instance_profile']
            }

        ec2 = get_ec2_client()

        # Attempt on all available subnets
        subnets = current_app.config['aws']['subnets'][:]
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

        autolive = app.config['aws'].get('auto_live', False)
        sitetag = app.config['general'].get('site_name', 'nebula')
        for instance in instances:
            print('Cluster start - tag')
            tags = [
                {'Key': sitetag, 'Value': 'true'},
                {'Key': 'User', 'Value': owner},
                {'Key': 'Profile', 'Value': profile['name']},
                {'Key': 'Group', 'Value': group_id}
            ]

            # Tag network devices- useful for cost exploration.
            for eni in instance.network_interfaces:
                print('tagging network interface')
                eni.create_tags(Tags=tags)

            # Tag attached devices. Volumes initialize slowly so scheduler another task.
            tag_instance_volumes.delay(instance.instance_id, tags)

            tags.append({'Key': 'Disk_Space', 'Value': str(size)})
            if label:
                tags.append({'Key': 'Label', 'Value': label})
            if shutdown:
                tags.append({'Key': 'Shutdown', 'Value': shutdown})
            if autolive:
                tags.append({'Key': 'Status', 'Value': 'Live'})
            instance.create_tags(Tags=tags)

        return True


@celery.task(rate_limit='120/m', expires=3600)
def tag_instance_volumes(instance_id, tags):
    print('Tagging instance volumes %s' % (instance_id,))
    ec2 = get_ec2_client()
    while True:
        instance = ec2.Instance(instance_id)
        if len(instance.block_device_mappings) > 0:
            for vol in instance.volumes.all():
                print('tagging volume')
                vol.create_tags(Tags=tags)
            return
        else:
            print('waiting for volumes to attach')
            time.sleep(5)


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


@celery.task(rate_limit='1/m', expires=60)
def shutdown_expired_instances():
    curtimestamp = int(datetime.now(pytz.utc).timestamp())
    instances = get_instance_list(state='running', terminated=False)
    for instance in instances:
        tags = get_tags_from_aws_object(instance)
        print('Beginning check of %s' % (instance.instance_id,))
        if 'Shutdown' in tags and tags['Shutdown'].isdigit():
            shutdown = int(tags['Shutdown'])
            print("%s (%s < %s)" % (instance.instance_id, curtimestamp, shutdown))
            if shutdown <= curtimestamp:
                print("Shutting down instance %s" % (instance.instance_id))
                stop_instance.delay(instance.instance_id)



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
    instance = get_instance(instance_id)
    if not instance:
        return False
    tags = get_tags_from_aws_object(instance)
    return 'User' in tags and tags['User'] == user


def get_instance(instance_id):
    ec2 = get_ec2_client()
    return ec2.Instance(instance_id)


def get_instance_tags(instance_id):
    ec2 = get_ec2_client()
    instances = ec2.instances.filter(InstanceIds=[instance_id])
    for instance in instances:
        return get_tags_from_aws_object(instance)


def get_tags_from_aws_object(ec2_object):
    tag_dict = {}
    if ec2_object.tags is None:
        return tag_dict
    for tag in ec2_object.tags:
        tag_dict[tag['Key']] = tag['Value']
    return tag_dict


def get_instance_list(owner=None, state=False, terminated=True, update_volumes=False):
    ec2 = get_ec2_client()
    sitetag = app.config['general'].get('site_name', 'nebula')
    filters = [{'Name': 'tag:%s' % (sitetag,), 'Values': ['true']}]

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


def key_normalize(instance_type):
    family = instance_type.split('.')[0]
    realcost = get_instance_description(instance_type)['price']
    price = str(int(realcost * 10000)).zfill(6)
    return "%s.%s" % (family, price)


@cache.cache()
def get_instance_types():
    if 'aws' in app.config and 'instances' in app.config['aws']:
        instance_conf = app.config['aws']['instances']
    else:
        instance_conf = {}

    data = get_instance_descriptions()
    instance_types = list(data.keys())

    filtered = []
    for instance_type in instance_types:
        instance_family = instance_type.split('.')[0]
        if 'whitelist' in instance_conf:
            if instance_family not in instance_conf['whitelist']:
                continue
        if 'blacklist' in instance_conf:
            if instance_family in instance_conf['blacklist']:
                continue
        filtered.append(instance_type)

    filtered.sort(key=key_normalize)
    return filtered


def get_instance_description(instance_type):
    descriptions = get_instance_descriptions()
    if instance_type in descriptions:
        costs = get_updated_prices()
        descriptions[instance_type]['price'] = costs[instance_type]
        return descriptions[instance_type]
    return False


@cache.cache()
def get_instance_descriptions():
    r = requests.get('https://tedivm.github.io/ec2details/api/ec2instances.json')
    return r.json()
