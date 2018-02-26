from nebula import app
from flask import render_template


@app.errorhandler(401)
def error_unauthorized(e):
    return show_error(401, 'Unauthorized')

@app.errorhandler(403)
def error_forbidden(e):
    return show_error(403, 'Forbidden')

@app.errorhandler(404)
def error_pagenotfound(e):
    return show_error(404, 'Page not found.')

@app.errorhandler(500)
def error_servererror(e):
    return show_error(500, 'Something may be on fire.')


def show_error(status, message='An unknown error has occured.'):
    return render_template('error.html', error_code=status, message=message), status
