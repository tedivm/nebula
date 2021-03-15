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
        if 'Linux' in data['prices']:
            if region in data['prices']['Linux']:
                if 'Shared' in data['prices']['Linux'][region]:
                    prices[instance_type] = data['prices']['Linux'][region]['Shared']
    return prices


@cache.cache()
def get_ami_root_size(ami):
    client = get_ec2_resource()
    image = client.Image(ami)
    if not image:
        return False
    for device in image.block_device_mappings:
        if device['DeviceName'] == image.root_device_name:
            if 'Ebs' in device and 'VolumeSize' in device['Ebs']:
                return device['Ebs']['VolumeSize']
    return False


def get_ec2_resource():
    with app.app_context():
        conn = getattr(g, '_ec2_resource', None)
        if conn is None:
            g._ec2_resource = boto3.resource('ec2', region_name=current_app.config['aws']['region'])
        return g._ec2_resource

def get_ec2_client():
    with app.app_context():
        conn = getattr(g, '_ec2_client', None)
        if conn is None:
            g._ec2_client = boto3.client('ec2', region_name=current_app.config['aws']['region'])
        return g._ec2_client


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
        filters = yaml.safe_load(profile['filter'])
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


def get_base_tags(profile_name, owner, group_id, size, label = False, shutdown = False, gpuidle = False):
    autolive = app.config['aws'].get('auto_live', False)
    sitetag = app.config['general'].get('site_name', 'nebula')
    tags = [
        {'Key': sitetag, 'Value': 'true'},
        {'Key': 'User', 'Value': owner},
        {'Key': 'Profile', 'Value': profile_name},
        {'Key': 'Group', 'Value': group_id},
        {'Key': 'Disk_Space', 'Value': str(size)}
    ]

    if label:
        tags.append({'Key': 'Label', 'Value': label})
    if shutdown:
        tags.append({'Key': 'Shutdown', 'Value': shutdown})
    if gpuidle:
        tags.append({'Key': 'GPU_Shutdown', 'Value': gpuidle})
    if autolive:
        tags.append({'Key': 'Status', 'Value': 'Live'})
    return tags


def get_launch_templates():
    sitetag = app.config['general'].get('site_name', 'nebula')
    filters = [{'Name': 'tag:%s' % (sitetag,), 'Values': ['true']}]

    client = boto3.client('ec2', region_name=current_app.config['aws']['region'])
    launch_templates = client.describe_launch_templates(
        Filters=filters
    )['LaunchTemplates']

    for template in launch_templates:
        tags = {}
        for tagpair in template['Tags']:
            tags[tagpair['Key']] = tagpair['Value']
        template['Tags'] = tags
    return launch_templates


@cache.cache(expire=60)
def get_launch_template_metadata(launch_template_id):
    sitetag = app.config['general'].get('site_name', 'nebula')
    filters = [{'Name': 'tag:%s' % (sitetag,), 'Values': ['true']}]

    client = boto3.client('ec2', region_name=current_app.config['aws']['region'])
    launch_templates = client.describe_launch_templates(
        LaunchTemplateIds=[launch_template_id],
        Filters=filters
    )['LaunchTemplates']

    if len(launch_templates) != 1:
        # Throw error if launch template doesn't exist or isn't unique
        return False

    launch_template = launch_templates[0]
    launch_template_versions = client.describe_launch_template_versions(
        LaunchTemplateId=launch_template_id,
        Versions=["$Default"]
    )["LaunchTemplateVersions"]

    if len(launch_template_versions) != 1:
        # Throw error if launch template version doesn't exist or isn't unique
        return False

    launch_template_version = launch_template_versions[0]
    return launch_template_version


def get_ami_from_launch_template(launch_template_id):
    metadata = get_launch_template_metadata(launch_template_id)
    return metadata['LaunchTemplateData']['ImageId']



def get_launch_instance_arguments_from_launch_template(launch_template_id, owner, group_id, size, label = False, shutdown = False, gpuidle = False):
    # Even though we have the launch template id we still do the lookup to validate that it is associated with this nebula instance
    launch_template_details = get_launch_template_metadata(launch_template_id)
    metadata = launch_template_details['LaunchTemplateData']
    startArgs = {
        'LaunchTemplate': {
            'LaunchTemplateId': launch_template_details['LaunchTemplateId']
        }
    }

    startArgs['MinCount'] = 1
    startArgs['MaxCount'] = 1

    # Merge tags from launch template with the nebula required tags.
    tags = get_base_tags(launch_template_details['LaunchTemplateId'], owner, group_id, size, label, shutdown, gpuidle)
    volume_tags = tags.copy()
    instance_tags = tags.copy()

    # To simplify the logic create a TagSpecifications object if it doesn't exist
    if 'TagSpecifications' not in metadata:
        metadata['TagSpecifications'] = []

    existing_instance_tags = [x for x in metadata['TagSpecifications'] if x['ResourceType'] == 'instance']
    if len(existing_instance_tags) > 0:
        instance_tags += existing_instance_tags[0]["Tags"]

    existing_volume_tags = [x for x in metadata['TagSpecifications'] if x['ResourceType'] == 'volume']
    if len(existing_volume_tags) > 0:
        volume_tags += existing_instance_tags[0]["Tags"]

    # Create tag specifications without the instance and volume tags
    startArgs["TagSpecifications"] = [x for x in metadata['TagSpecifications'] if x['ResourceType'] != 'volume' and x['ResourceType'] != 'instance']

    # Add back the instance and volume tags now that they have been merged with the nebula specific ones
    startArgs["TagSpecifications"].append({ 'ResourceType': 'instance', 'Tags': clean_dupe_tags(instance_tags)})
    startArgs["TagSpecifications"].append({ 'ResourceType': 'volume', 'Tags': clean_dupe_tags(volume_tags)})

    return startArgs


def get_launch_instance_arguments_from_profile(profile_id, owner, group_id, size, label = False, shutdown = False, gpuidle = False):
    # within this block, current_app points to app.
    profile = profiles.get_profile(profile_id)
    userdata = profile['userdata']
    ImageID = get_ami_from_profile(profile_id)

    startArgs = {
        'DryRun': False,
        'ImageId': ImageID,
        'MinCount': 1,
        'MaxCount': 1,
        'UserData': userdata,
        'Monitoring': {
            'Enabled': True
        },
        'DisableApiTermination': False,
        'InstanceInitiatedShutdownBehavior': 'stop',
        'EbsOptimized': app.config['aws'].get('ebs_optimized', False),
    }

    if 'subnets' not in current_app.config['aws']:
        raise ValueError("SUBNET_ID must be saved in configuration")

    if 'security_group' in current_app.config['aws']:
        startArgs['SecurityGroupIds'] = [current_app.config['aws']['security_group']]

    if 'iam_instance_profile' in current_app.config['aws']:
        startArgs['IamInstanceProfile'] = {
            'Arn': current_app.config['aws']['iam_instance_profile']
        }

    tags = get_base_tags(profile['name'], owner, group_id, size, label, shutdown, gpuidle)

    if profile['tags']:
        for line in profile['tags'].splitlines():
            if len(line) > 3 and '=' in line:
                tag_name, tag_value = line.split('=', 1)
                tags.append({'Key': tag_name, 'Value': tag_value})


    startArgs['TagSpecifications'] = [
        { 'ResourceType': 'instance', 'Tags': tags},
        { 'ResourceType': 'volume', 'Tags': tags},
    ]

    return startArgs


def clean_dupe_tags(tags):
    return [dict(t) for t in {tuple(d.items()) for d in tags}]


@celery.task(expires=300, acks_late=False)
def launch_instance(group_id, profile_id, instancetype, owner, size=120, label = False, shutdown = False, gpuidle = False):
    print('Launching %s for %s with profile "%s"' % (instancetype, owner, profile_id))

    with app.app_context():
        # within this block, current_app points to app.

        if current_app.config['aws'].get('use_launch_templates', False):
            startArgs = get_launch_instance_arguments_from_launch_template(profile_id, owner, group_id, size, label, shutdown, gpuidle)
        else:
            startArgs = get_launch_instance_arguments_from_profile(profile_id, owner, group_id, size, label, shutdown, gpuidle)

        startArgs['InstanceType'] = instancetype
        startArgs['BlockDeviceMappings'] = [
            {
                'DeviceName': '/dev/sda1',
                'Ebs': {
                    'VolumeSize': size,
                    'VolumeType': 'gp2'
                }
            }
        ]


        ec2 = get_ec2_resource()

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


        # Wait for all machine requests to process so we can tag the network interfaces.
        while True:
            launched = True
            for instance in instances:
                if instance.state == 16:
                    launched = False
            if launched:
                break
            time.sleep(5)

        # Pull out "instance" tags and apply them to the network interface
        existing_instance_tags = [x for x in startArgs['TagSpecifications'] if x['ResourceType'] == 'instance']
        if len(existing_instance_tags) > 0:
            for instance in instances:
                # Tag network devices- useful for cost exploration.
                for eni in instance.network_interfaces:
                    print('tagging network interface')
                    eni.create_tags(Tags=existing_instance_tags[0]['Tags'])

        return True


@celery.task(expires=3600)
def tag_instance_volumes(instance_id, tags):
    print('Tagging instance volumes %s' % (instance_id,))
    ec2 = get_ec2_resource()
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


@celery.task(expires=3600)
def stop_instance(instance_id):
    print('Stopping instance %s' % (instance_id,))
    ec2 = get_ec2_resource()
    ec2.instances.filter(InstanceIds=[instance_id]).stop()
    remove_instance_tag(instance_id, 'Shutdown')


@celery.task(expires=300)
def start_instance(instance_id):
    print('Starting instance %s' % (instance_id,))
    ec2 = get_ec2_resource()
    ec2.instances.filter(InstanceIds=[instance_id]).start()
    remove_instance_tag(instance_id, 'Shutdown')


@celery.task(expires=300)
def reboot_instance(instance_id):
    print('Rebooting instance %s' % (instance_id,))
    ec2 = get_ec2_resource()
    ec2.instances.filter(InstanceIds=[instance_id]).reboot()


@celery.task(expires=300)
def change_instance_type(instance_id, instance_type):
    print('Changing instance %s\'s instance type to %s' % (instance_id, instance_type))
    ec2 = get_ec2_resource()
    ec2.modify_instance_attribute(InstanceId=instance_id, Attribute='instanceType', Value=instance_type)


@celery.task(rate_limit='1/m', expires=60)
def tag_active_instances():
    curtimestamp = int(datetime.now(pytz.utc).timestamp())
    instances = get_instance_list(state='running')
    for instance in instances:
        tag_instance.delay(instance.instance_id, "LastOnline", curtimestamp)


@celery.task(rate_limit='1/m', expires=60)
def shutdown_expired_instances():
    instance_ids = set([])

    # Get instances with Shutdown tag
    instances = get_instance_list(state='running', terminated=False, tag_keys=['Shutdown'])
    for instance in instances:
        instance_ids.add(instance.instance_id)

    # Get instances with GPU_Shutdown tag
    instances = get_instance_list(state='running', terminated=False, tag_keys=['GPU_Shutdown'])
    for instance in instances:
        instance_ids.add(instance.instance_id)

    # Schedule shutdown check for all relevant instances
    for instance_id in instance_ids:
        shutdown_expired_instance.delay(instance_id)


@celery.task()
def shutdown_expired_instance(instance_id):
    instance = get_instance(instance_id)
    curtimestamp = int(datetime.now(pytz.utc).timestamp())

    print('Beginning check of %s' % (instance.instance_id,))

    tags = get_tags_from_aws_object(instance)
    if 'Shutdown' in tags and tags['Shutdown'].isdigit() and int(tags['Shutdown']) > 0:
        shutdown = int(tags['Shutdown'])
        print("%s (%s < %s)" % (instance.instance_id, curtimestamp, shutdown))
        if shutdown <= curtimestamp:
            print("Shutting down instance %s" % (instance.instance_id))
            stop_instance.delay(instance.instance_id)
            return

    if 'GPU_Shutdown' in tags and tags['GPU_Shutdown'].isdigit() and int(tags['GPU_Shutdown']) > 0:
        # If the instance has no GPUs then don't check for idle gpu.
        instance_details = get_instance_description(instance.instance_type)
        if 'gpu' not in instance_details or instance_details['gpu'] < 1:
            return

        # Don't shut down if instance has not been up for at least an hour.
        if int(instance.launch_time.timestamp()) + (60*60) > curtimestamp:
            return

        last_use = instance.launch_time.timestamp()
        if 'GPU_Last_Use' in tags:
            last_use = tags['GPU_Last_Use']

        if curtimestamp - last_use > (int(tags['GPU_Shutdown']) * 60):
            print("Shutting down instance %s" % (instance.instance_id))
            stop_instance.delay(instance.instance_id)
            return



@celery.task()
def terminate_instance(instance_id):
    print('Terminating instance %s' % (instance_id,))
    ec2 = get_ec2_resource()
    ec2.instances.filter(InstanceIds=[instance_id]).terminate()

@celery.task()
def tag_instance(instance_id, tag, value):
    ec2 = get_ec2_resource()
    ec2.instances.filter(InstanceIds=[instance_id]).create_tags(
        Tags=[
            { 'Key': tag, 'Value': value }
        ]
    )

@celery.task()
def multi_tag_instance(instance_id, tags):
    ec2 = get_ec2_resource()
    tagList = []
    for key in tags:
        tagList.append({ 'Key': key, 'Value': tags[key] })
    ec2.instances.filter(InstanceIds=[instance_id]).create_tags(
        Tags=tagList
    )


@cache.cache()
def is_owner(instance_id, user):
    instance = get_instance(instance_id)
    if not instance:
        return False
    tags = get_tags_from_aws_object(instance)
    return 'User' in tags and tags['User'] == user


def get_instance(instance_id):
    ec2 = get_ec2_resource()
    return ec2.Instance(instance_id)


def get_instance_tags(instance_id):
    ec2 = get_ec2_resource()
    instances = ec2.instances.filter(InstanceIds=[instance_id])
    for instance in instances:
        return get_tags_from_aws_object(instance)


def remove_instance_tag(instance_id, tag_name):
    tags = get_instance_tags(instance_id)
    if tag_name in tags:
        ec2 = get_ec2_client()
        ec2.delete_tags(Resources=[instance_id],Tags=[{"Key": tag_name}])


def get_tags_from_aws_object(ec2_object):
    tag_dict = {}
    if ec2_object.tags is None:
        return tag_dict
    for tag in ec2_object.tags:
        tag_dict[tag['Key']] = tag['Value']
    return tag_dict


def get_instance_list(owner=None, state=False, terminated=True, update_volumes=False, tag_keys=False):
    ec2 = get_ec2_resource()
    sitetag = app.config['general'].get('site_name', 'nebula')
    filters = [{'Name': 'tag:%s' % (sitetag,), 'Values': ['true']}]

    if tag_keys:
        for tag_name in tag_keys:
            filters.append({'Name': 'tag-key', 'Values': [tag_name]})

    if state:
        if isinstance(state, str):
            state = [state]
        filters.append({'Name':'instance-state-name', 'Values':state})
    elif not terminated:
        states = ['pending', 'running', 'shutting-down', 'stopping', 'stopped', 'rebooting']
        filters.append({'Name':'instance-state-name', 'Values':states})
    if owner:
        filters.append({'Name':'tag:User', 'Values':[owner]})

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
    ec2 = get_ec2_resource()
    filters = [{ 'Name': 'tag:Group', 'Values': [group_id] }]
    instances = ec2.instances.filter(Filters=filters)
    return list(instances)


def key_normalize(instance_type):
    family = instance_type.split('.')[0]
    description = get_instance_description(instance_type)
    if not description:
        return 'z'
    if description['price']:
        price = str(int(description['price'] * 10000)).zfill(6)
    else:
        price = 'z'
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
    if instance_type not in descriptions:
        return False
    costs = get_updated_prices()
    if instance_type in costs:
        descriptions[instance_type]['price'] = costs[instance_type]
    else:
        descriptions[instance_type]['price'] = False
    return descriptions[instance_type]



@cache.cache()
def get_instance_descriptions():
    r = requests.get('https://tedivm.github.io/ec2details/api/ec2instances.json')
    return r.json()
