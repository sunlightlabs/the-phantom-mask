#!/bin/bash

if [ -z "$PROJECT_DIR" ]; then
    export PROJECT_DIR=/projects/the-phantom-mask
fi

function activate_virtualenv()
{
    if [ ! -f .venv/bin/activate ]; then virtualenv .venv; fi; source .venv/bin/activate
}

function version_control()
{
    git pull
    pip install -r requirements.txt
}

function stop_gunicorn()
{
    GUNICORN_PID=`cat gunicorn.pid`
    kill $GUNICORN_PID
    bin/pwait $GUNICORN_PID
}

function start_gunicorn()
{
    PHANTOM_ENVIRONMENT=prod gunicorn -w 4 run:application --daemon -p gunicorn.pid -b unix:$PROJECT_DIR/gunicorn.sock
}

function stop_celery()
{
    CELERY_PID=`cat celery.pid`
    kill $CELERY_PID
    bin/pwait $CELERY_PID
}

function start_celery()
{
    PHANTOM_ENVIRONMENT=prod celery -A app.scheduler worker --loglevel=info -D --pidfile=celery.pid
}

cd $PROJECT_DIR

if [ $# -eq 0 ]
  then
        activate_virtualenv
        version_control
        stop_gunicorn
        start_gunicorn
        stop_celery
        start_celery
  else
        $@
fi