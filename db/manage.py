#!/usr/bin/env python
from migrate.versioning.shell import main
import os
from importlib.machinery import SourceFileLoader

settings_file = os.environ['SETTINGS']
settings = SourceFileLoader("module.name", settings_file).load_module()
if __name__ == '__main__':
    db_url='postgresql://%s:5432/%s?user=%s&password=%s' % (settings.DB_HOST, settings.DB, settings.DB_USERNAME, settings.DB_PASSWORD )
    main(url=db_url, repository='db', debug='False')
