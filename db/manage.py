#!/usr/bin/env python
from migrate.versioning.shell import main
import os
from importlib.machinery import SourceFileLoader
from migrate.exceptions import DatabaseAlreadyControlledError
import yaml

if 'SETTINGS' in os.environ:
    with open(os.environ['SETTINGS'], 'r') as stream:
        settings = yaml.load(stream)['postgres']

if __name__ == '__main__':
    db_url = 'postgresql://%s:5432/%s?user=%s&password=%s' % (settings['host'], settings['database'], settings['username'], settings['password'])
    try:
        main(url=db_url, repository='db', debug='False')
    except DatabaseAlreadyControlledError:
        exit(0)
