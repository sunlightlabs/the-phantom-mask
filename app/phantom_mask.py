from config import settings
from flask.ext.sqlalchemy import SQLAlchemy
import os

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


def route_app(app):
    """
    Adds routes to the app

    @param app: Flask app
    @type app: flask.Flask
    @return: Flask app
    @rtype: flask.Flask
    """
    # csrf protection
    from flask_wtf.csrf import CsrfProtect
    csrf = CsrfProtect()
    csrf.init_app(app)

    from urls import app_router
    from urls import postmark_router
    app.register_blueprint(app_router, url_prefix=settings.BASE_PREFIX)
    app.register_blueprint(postmark_router, url_prefix=settings.BASE_PREFIX)
    csrf.exempt(postmark_router)

    return app


db = SQLAlchemy(create_app())