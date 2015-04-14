from fabric.api import local
from fabric.api import *
from fabric.contrib.console import confirm
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
    push()


def deploy():
    prepare_deploy()
    with cd(settings.DEPLOY_SERVER_APP_PATH):
        run('git pull')
        run('if [ ! -f .venv/bin/activate ]; then source .venv/bin/activate; else virtualenv .venv; fi')
        run('pip install -r requirements.txt')
        put('config/settings.py', settings.DEPLOY_SERVER_APP_PATH + '/config/settings.py')

        run('')

