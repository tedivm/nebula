#! /usr/bin/env bash

# Let the DB start
echo 'Wait for other services to come online.'
sleep 10;

echo 'Performing any database migrations.'
python /app/db/manage.py version_control
python /app/db/manage.py upgrade
