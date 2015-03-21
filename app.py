from flask import Flask
from flask.ext.sqlalchemy import SQLAlchemy
from urls import app_router
from urls import postmark_router
from flask_wtf.csrf import CsrfProtect

# create an instance of the Flask class with name = __name__ or the name of this file
app = Flask(__name__)
# set debug to true so we see error dumps in the browser
app.debug = True

app.secret_key = 'WLEKJLKJRE#$324234q/qwe,2342j3lqwe,/qwq1LK3dMEW><>'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////tmp/test.db'

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