from fabric.api import local
from fabric.api import *
from fabric.contrib.console import confirm

def prepare_deploy():
    test()
    add_and_commit()
    push()

def test():
    local("python tests/phantom_mask_tests.py")


def add_and_commit():
    local("git add -p && git commit")


def push():
    local("git push origin master")

"""

def deploy():
    code_dir = '/home/crd/the_phantom_mask'
    with settings(warn_only=True):
        if run("test -d %s" % code_dir).failed:
            run("git clone https://github.com/sunlightlabs/the-phantom-mask.git %s" % code_dir)
    with cd(code_dir):
        run("git pull origin master")
"""