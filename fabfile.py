from fabric.api import *
from config import settings
import sys


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
    def inner(*args):
        with cd(settings.DEPLOY_SERVER_APP_PATH):
            activate = settings.VIRTUAL_ENV_PATH + '/bin/activate'
            with prefix('if [ ! -f ' + activate + ' ]; then virtualenv ' + settings.VIRTUAL_ENV_PATH + '; fi; source ' + activate):
                return func(*args)
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
def run_deploy_function(name):
    run('bin/deploy.sh ' + name)


def start_celery():
    run_deploy_function(sys._getframe().f_code.co_name)


def stop_celery():
    run_deploy_function(sys._getframe().f_code.co_name)


def restart_celery():
    stop_celery()
    start_celery()


def start_gunicorn():
    run_deploy_function(sys._getframe().f_code.co_name)


def stop_gunicorn():
    run_deploy_function(sys._getframe().f_code.co_name)


def restart_gunicorn():
    stop_gunicorn()
    start_gunicorn()


def version_control():
    run_deploy_function(sys._getframe().f_code.co_name)


@cd_and_prefix
def reset_database():
    run('PHANTOM_ENVIRONMENT=prod python tasks/admin.py reset_database')


def deploy_run():
    version_control()
    restart_celery()
    restart_gunicorn()


def deploy():
    prepare_deploy()
    deploy_run()