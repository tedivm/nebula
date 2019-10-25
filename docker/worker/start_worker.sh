#!/usr/bin/env bash

BASE_COMMAND="celery -A nebula.celery worker --loglevel=info --autoscale=10,2 --without-gossip --without-mingle"

if [ "$DISABLE_BEAT" = "true" ]
then
  echo 'Launching celery worker without beat'
  $BASE_COMMAND
else
  echo 'Launching celery worker with beat enabled'
  rm -f /home/nebula/celerybeat-schedule
  $BASE_COMMAND -B -s /home/nebula/celerybeat-schedule
fi
