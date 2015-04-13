from flask import Blueprint
import views
import actions

app_router = Blueprint('app_router', __name__, template_folder='templates')
app_router.route('/validate/<token>', methods=['GET', 'POST'])(views.update_user_address)
app_router.route('/confirm_reps/<token>', methods=['GET', 'POST'])(views.confirm_reps)
app_router.route('/address_changed/<token>', methods=['GET'])(views.address_changed)
app_router.route('/legislator_index', methods=['GET'])(views.legislator_index)
app_router.route('/ajax/autofill_address', methods=['POST'])(actions.autofill_address)

postmark_router = Blueprint('postmark_router', __name__, template_folder='templates')
postmark_router.route('/postmark/inbound', methods=['POST'])(views.postmark_inbound)