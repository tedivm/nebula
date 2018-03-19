#! /usr/bin/env bash

# Let the DB start
database=`cat SETTINGS | sed -rn "s/DB_HOST = '(.+)'/\1/p"`

echo "Waiting for postgres to be available at host '${database}'"
while ! pg_isready -h ${database} > /dev/null 2> /dev/null; do
  sleep 1
done

echo 'Performing any database migrations.'
python /app/db/manage.py version_control
python /app/db/manage.py upgrade
