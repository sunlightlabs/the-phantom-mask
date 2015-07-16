from os.path import dirname, realpath, abspath, join
from os import walk
import os
import jinja2
import helpers

def abs_file_directory(file):
    dirname(realpath(file))


def absoluteFilePaths(directory):
    for dirpath, _,filenames in walk(directory):
        for f in filenames:
            yield abspath(join(dirpath, f))


def render_without_request(template_name, **template_vars):
    """
    Usage is the same as flask.render_template:

    render_without_request('my_template.html', var1='foo', var2='bar')
    """
    from phantom_mask import create_app, config_ext
    with config_ext(create_app()).app_context():
        return helpers.render_template_wctx(template_name, **template_vars)

class DummyEmail(object):

    def __init__(self, pmmail):
        self.pmmail = pmmail

    @property
    def subject(self):
        return self.pmmail.subject

    @property
    def html_body(self):
        return self.pmmail.html_body

    def send(self):
        return None