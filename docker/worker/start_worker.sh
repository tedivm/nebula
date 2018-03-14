#!/usr/bin/env bash

if [ "$DISABLE_BEAT" = "true" ]
then
  celery -A nebula.celery worker --loglevel=info --autoscale=10,2
else
  celery -A nebula.celery worker --loglevel=info --autoscale=10,2 -B -s /home/nebula/celerybeat-schedule
fi
