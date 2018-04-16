#!/usr/bin/env bash

if [ "$DISABLE_BEAT" = "true" ]
then
  echo 'Launching celery worker without beat'
  celery -A nebula.celery worker --loglevel=info --autoscale=10,2
else
  echo 'Launching celery worker with beat enabled'
  rm -f /home/nebula/celerybeat-schedule
  celery -A nebula.celery worker --loglevel=info --autoscale=10,2 -B -s /home/nebula/celerybeat-schedule
fi
