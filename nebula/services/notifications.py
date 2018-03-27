import json
import smtplib
import email.message
from nebula import app, celery
from nebula.services import aws
from flask import render_template


SMTP_DOMAIN = app.config.get('SMTP_DOMAIN')
SMTP_USERNAME = app.config.get('SMTP_USERNAME')
SMTP_PASSWORD = app.config.get('SMTP_PASSWORD')
SMTP_ORIGIN = app.config.get('SMTP_ORIGIN')
NOTIFICATION_THRESHOLD = app.config.get('NOTIFICATION_THRESHOLD', 500)


def get_total_costs():
    """Return a dictionary of total instance uptime and costs by user."""
    prices = aws.get_updated_prices()
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


@celery.task(rate_limit='1/m', expires=300)
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
    if not SMTP_DOMAIN or not SMTP_ORIGIN:
        return False

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
