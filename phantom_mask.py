from flask import Flask
from flask_wtf.csrf import CsrfProtect
from config import settings
from flask.ext.sqlalchemy import SQLAlchemy

def create_app():
    # create an instance of the Flask class with name = __name__ or the name of this file
    app = Flask(__name__)
    # set debug to true so we see error dumps in the browser
    app.debug = settings.APP_DEBUG

    app.secret_key = settings.APP_SECRET_KEY
    app.config['SQLALCHEMY_DATABASE_URI'] = settings.DATABASE_URI
    app.config['BASE_URL'] = settings.BASE_URL
    app.config['SQLALCHEMY_ECHO'] = True

    # csrf protection
    csrf = CsrfProtect()
    csrf.init_app(app)

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
    app.run()