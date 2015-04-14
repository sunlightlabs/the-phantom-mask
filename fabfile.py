from fabric.api import *
from config import settings

# the user to use for the remote commands
env.user = settings.DEPLOY_SERVER_USER
# the servers where the commands are executed
env.hosts = settings.DEPLOY_SERVER_HOSTS


def test():
    local("python tests/phantom_mask_tests.py")

def add_and_commit():
    local("git add -p && git commit")

def push(branch='master'):
    local("git push origin " + branch)

def prepare_deploy(branch='master'):
    test()
    add_and_commit()
    push(branch)


def cd_and_prefix(func):
    def inner():
        with cd(settings.DEPLOY_SERVER_APP_PATH):
            with prefix('if [ ! -f .venv/bin/activate ]; then virtualenv .venv; fi; source .venv/bin/activate'):
                return func()
    return inner


def kill_process_and_wait(process):
    try:
        pid = run('cat ' + process + '.pid')
        run("kill `cat " + process + ".pid`")
        run('bin/pwait ' + pid)
    except:
        print 'Unable to kill ' + process + ' because there is no PID file.'
    return True

@cd_and_prefix
def stop_celery():
    kill_process_and_wait('celery')

@cd_and_prefix
def start_celery():
    run('celery -A app.scheduler worker --loglevel=info -D --pidfile=celery.pid')

@cd_and_prefix
def restart_celery():
    stop_celery()
    start_celery()

@cd_and_prefix
def stop_gunicorn():
    kill_process_and_wait('gunicorn')

@cd_and_prefix
def reset_database():
    run('PHANTOM_ENVIRONMENT=prod python tasks/admin.py reset_database')

@cd_and_prefix
def start_gunicorn():
    run('PHANTOM_ENVIRONMENT=prod gunicorn -w 4 run:application --daemon -p gunicorn.pid')

@cd_and_prefix
def restart_gunicorn():
    stop_gunicorn()
    start_gunicorn()

@cd_and_prefix
def deploy_run():
    run('git pull')
    put('config/settings.py', settings.DEPLOY_SERVER_APP_PATH + '/config/settings.py')
    run('pip install -r requirements.txt')
    restart_gunicorn()

def deploy():
    prepare_deploy()
    deploy_run()