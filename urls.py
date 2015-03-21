from flask import Blueprint, render_template, abort
import views

app_router = Blueprint('app_router', __name__, template_folder='templates')
app_router.route('/verify/<verification_token>', methods=['GET','POST'])(views.verify_message)

postmark_router = Blueprint('postmark_router', __name__, template_folder='templates')
postmark_router.route('/postmark/', methods=['POST'])(views.postmark)