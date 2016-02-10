import os
from flask.ext.sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CsrfProtect
from config import settings
import jinja2
import logging
from logging import handlers

env = os.environ.get('PHANTOM_ENVIRONMENT', 'dev' if settings.APP_DEBUG else 'prod')


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
    app.config['RECAPTCHA_PUBLIC_KEY'] = settings.RECAPTCHA_PUBLIC_KEY
    app.config['RECAPTCHA_PRIVATE_KEY'] = settings.RECAPTCHA_PRIVATE_KEY
    app.config['SERVER_NAME'] = settings.BASE_URL

    # logging
    handler = handlers.RotatingFileHandler(settings.LOGGING_LOCATION, maxBytes=10000000, backupCount=10)
    handler.setLevel(logging.ERROR)
    formatter = logging.Formatter(settings.LOGGING_FORMAT)
    handler.setFormatter(formatter)
    app.logger.addHandler(handler)

    app.jinja_options['extensions'].append('jinja2.ext.loopcontrols')
    my_loader = jinja2.ChoiceLoader([
        app.jinja_loader,
        jinja2.FileSystemLoader([os.path.dirname(os.path.abspath(__file__)) + '/static']),
    ])
    app.jinja_loader = my_loader

    return app


def config_ext(app):
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