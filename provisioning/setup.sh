#!/usr/bin/env bash

# Get real directory in case of symlink
if [[ -L "${BASH_SOURCE[0]}" ]]
then
  DIR="$( cd "$( dirname $( readlink "${BASH_SOURCE[0]}" ) )" && pwd )"
else
  DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
fi
cd $DIR/..

apt-get update
apt-get -f -y install git nano man # some vagrant boxes are pretty minimal
apt-get -f -y install python3-pip python3-dev
apt-get -f -y install virtualenv
apt-get -f -y install postgresql postgresql-contrib libpq-dev
apt-get -f -y install rabbitmq-server

sudo -u postgres psql -c 'CREATE EXTENSION IF NOT EXISTS "uuid-ossp";'
sudo -u postgres psql -c 'CREATE EXTENSION IF NOT EXISTS "pgcrypto";'

sudo -u postgres psql -c "CREATE USER nebula WITH PASSWORD 'nebula';"
sudo -u postgres psql -c "create database \"nebula\" with owner \"nebula\" encoding='utf8' template template0"

useradd -N -M --system -s /bin/bash nebula
groupadd nebula
adduser nebula nebula


virtualenv -p /usr/bin/python3 env
source env/bin/activate
pip install -r requirements.txt

export SETTINGS=/vagrant/settings
export FLASK_APP=/vagrant/nebula/nebula.py
python db/manage.py version_control
python db/manage.py upgrade
