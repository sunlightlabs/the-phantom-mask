from flask import Blueprint
import views

app_router = Blueprint('app_router', __name__, template_folder='templates')
app_router.route('/verify/<verification_token>', methods=['GET', 'POST'])(views.verify_message)
app_router.route('/legislator_index/', methods=['GET'])(views.legislator_index)

postmark_router = Blueprint('postmark_router', __name__, template_folder='templates')
postmark_router.route('/postmark/inbound', methods=['POST'])(views.postmark)