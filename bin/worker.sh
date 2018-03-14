#!/usr/bin/env bash

# Get real directory in case of symlink
if [[ -L "${BASH_SOURCE[0]}" ]]
then
  DIR="$( cd "$( dirname $( readlink "${BASH_SOURCE[0]}" ) )" && pwd )"
else
  DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
fi

source $DIR/envvar
cd $DIR/..

celery -A nebula.celery worker -B --loglevel=info --autoscale=10,2