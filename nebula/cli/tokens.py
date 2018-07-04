import click
from nebula import app
from nebula.models import tokens

@app.cli.command()
@click.argument('token_id')
@click.argument('token')
def verify_token(token_id, token):
    click.echo(tokens.verify(token_id, token))
