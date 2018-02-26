import json
import smtplib
import email.message
import awspricingfull
from nebula import app, celery
from nebula.services import aws
from flask import render_template
from celery.task.schedules import crontab
from celery.decorators import periodic_task


SMTP_DOMAIN = app.config['SMTP_DOMAIN']
SMTP_USERNAME = app.config['SMTP_USERNAME']
SMTP_PASSWORD = app.config['SMTP_PASSWORD']
SMTP_ORIGIN = app.config['SMTP_ORIGIN']
NOTIFICATION_THRESHOLD = app.config['NOTIFICATION_THRESHOLD']


def get_updated_prices():
    """Return a dictionary of updated EC2 Linux instance prices."""
    ec2_prices = awspricingfull.EC2Prices()
    price_list = json.loads(ec2_prices.return_json('ondemand'))

    us_west_2_prices = [x for x in price_list['regions'] if x['region'] == 'us-west-2'][0]
    linux_prices = [x for x in us_west_2_prices['instanceTypes'] if x['os'] == 'linux']

    prices = {}
    for instance in linux_prices:
        prices[instance['type']] = instance['price']

    return prices


def get_total_costs():
    """Return a dictionary of total instance uptime and costs by user."""
    prices = get_updated_prices()
    servers = aws.get_instance_list(terminated=False)

    user_bill = {}
    for server in servers:
        tags = aws.get_tags_from_aws_object(server)
        if 'Status' in tags and tags['Status'] == 'Live':
            user = tags['User']
            cost_of_instance = (prices[server.instance_type] / 3600) * aws.seconds_billed(server)

            if user not in user_bill:
                user_bill[user] = {'num_instances': 1,
                                   'total_uptime': aws.seconds_billed(server) / 3600,
                                   'total_cost': cost_of_instance}
            else:
                user_bill[user]['num_instances'] += 1
                user_bill[user]['total_uptime'] += aws.seconds_billed(server) / 3600
                user_bill[user]['total_cost'] += cost_of_instance

    return user_bill


def as_currency(amount):
    """Helper function to format a float as $ currency."""
    if amount >= 0:
        return '${:,.2f}'.format(amount)
    else:
        return '-${:,.2f}'.format(-amount)


def notify_users():
    """Notify users of billing information."""
    user_bill = get_total_costs()
    for user, info in user_bill.items():
        if info['total_cost'] > int(NOTIFICATION_THRESHOLD):

            # Prepare body of message
            with app.app_context():
                text = render_template('email_notification.html',
                                       name=user,
                                       num_instances=info['num_instances'],
                                       total_cost=as_currency(info['total_cost']))

            # Send notification email
            email = '%s@i.example' % (user,)
            send_notification_email('Nebula Billing Notification', text, email)


def send_notification_email(subject, text, recipient):
    """Send a notification email over smtp with the specified information."""
    # Prepare email metadata
    msg = email.message.Message()
    msg['Subject'] = subject
    msg['From'] = SMTP_ORIGIN
    msg.add_header('Content-Type', 'text/html')
    msg.set_payload(text)

    # Connect to smtp and send the message
    server = smtplib.SMTP(SMTP_DOMAIN)
    server.starttls()
    server.login(SMTP_USERNAME, SMTP_PASSWORD)
    server.sendmail(SMTP_ORIGIN, recipient, msg.as_string())
