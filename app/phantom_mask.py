import os
from flask.ext.sqlalchemy import SQLAlchemy
from flask_admin import Admin
from flask_wtf.csrf import CsrfProtect
from config import settings

env = os.environ.get('PHANTOM_ENVIRONMENT', 'dev')

def create_app():
    """
    Creates the Flask app instance

    @return: Flask app
    @rtype: flask.Flask
    """
    from flask import Flask
    app = Flask(__name__)
    # set debug to true so we see error dumps in the browser
    app.debug = settings.APP_DEBUG
    app.secret_key = settings.APP_SECRET_KEY
    app.config['SQLALCHEMY_DATABASE_URI'] = settings.DATABASE[env]['uri']
    app.config['BASE_URL'] = settings.BASE_URL
    app.config['SQLALCHEMY_ECHO'] = settings.DATABASE[env]['echo']
    app.jinja_options['extensions'].append('jinja2.ext.loopcontrols')
    return app


def config_app(app):
    """
    Configures the app with extensions.

    @param app: Flask app
    @type app: flask.Flask
    @return: Flask app
    @rtype: flask.Flask
    """
    from urls import create_app_router, create_postmark_router, create_admin
    from views import login_manager

    csrf = CsrfProtect(app)

    create_postmark_router(app, csrf)
    create_app_router(app)

    login_manager.init_app(app)
    login_manager.session_protection = "strong"

    create_admin(app)

    return app

db = SQLAlchemy(create_app())