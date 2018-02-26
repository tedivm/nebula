from flask import Flask, session, request, render_template, abort
from nebula import app
from nebula.routes.decorators import login_required
from nebula.services import notifications

template_signed = '''
%s
<br><br>
From user <b>%s</b>:
<br><br>
%s
'''

template_anon = '''
%s
<br><br>
%s
'''

@app.route('/feedback', methods=["GET", "POST"])
@login_required
def feedback():
    print('hi')
    if 'FEEDBACK_EMAIL' not in app.config:
        abort(404)

    if request.method == 'POST':
        recipient = app.config['FEEDBACK_EMAIL']
        topic = request.form['topic']
        message = request.form['message']
        subject = 'Feedback from nebula: %s' % (topic,)
        if 'anonymous' not in request.form:
            body = template_signed % (topic, session['username'], message)
        else:
            body = template_anon % (topic, message)

        notifications.send_notification_email(subject, body, recipient)
        return render_template("feedback_acknowledgement.html")
    return render_template("feedback.html")
