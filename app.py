from flask import Flask
from flask.ext.sqlalchemy import SQLAlchemy
from urls import app_router
from urls import postmark_router
from flask_wtf.csrf import CsrfProtect
from config import settings

# create an instance of the Flask class with name = __name__ or the name of this file
app = Flask(__name__)
# set debug to true so we see error dumps in the browser
app.debug = settings.APP_DEBUG

app.secret_key = settings.APP_SECRET_KEY
app.config['SQLALCHEMY_DATABASE_URI'] = settings.DATABASE_URI

# csrf protection
csrf = CsrfProtect()
db = SQLAlchemy(app)

app.register_blueprint(app_router)
app.register_blueprint(postmark_router)

# launch the app
if __name__ == '__main__':
    csrf.init_app(app)
    csrf.exempt(postmark_router)
    app.run()