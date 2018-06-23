#!/usr/bin/env bash


if [ -d /home/nebula/.aws ]; then
  cp -Rf /home/nebula/.aws /root/
  chown -R root:root /root/.aws
fi

# Let the DB start
database=`/app/get_database.py`
echo "Waiting for postgres to be available at host '${database}'"
while ! pg_isready -h ${database} > /dev/null 2> /dev/null; do
  sleep 1
done

echo 'Performing any database migrations.'
python /app/db/manage.py version_control
python /app/db/manage.py upgrade
