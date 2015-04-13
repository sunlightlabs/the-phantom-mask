from config import settings
from flask.ext.sqlalchemy import SQLAlchemy
import os

env = os.environ.get('PHANTOM_ENVIRONMENT', 'dev')


def create_app():
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
    # csrf protection
    from flask_wtf.csrf import CsrfProtect
    csrf = CsrfProtect()
    csrf.init_app(app)

    # add routes
    from urls import app_router
    from urls import postmark_router
    app.register_blueprint(app_router)
    app.register_blueprint(postmark_router)
    csrf.exempt(postmark_router)

    return app

app = create_app()
db = SQLAlchemy(app)

# launch the app
if __name__ == '__main__':
    config_app(app).run()