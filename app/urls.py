from flask import Blueprint, g
from flask_admin import Admin

import views
import actions
from config import settings
from helpers import render_template_wctx


def register_with_app(inst_func):

    def register(app=None, csrf=None):
        obj = inst_func(app, csrf)
        if csrf is not None:
            if type(obj) is Blueprint:
                csrf.exempt(obj)
        if app is not None:
            if type(obj) is Blueprint:
                app.register_blueprint(obj, url_prefix=settings.BASE_PREFIX)
            else:
                obj.init_app(app)
        return obj

    return register

@register_with_app
def create_admin(app, csrf):
    from models import db, User, Legislator, AdminUser, UserMessageInfo, Message, MessageLegislator, Topic
    from flask.ext.admin.menu import MenuLink

    admin = Admin(index_view=views.MyAdminIndexView(url=settings.BASE_PREFIX + '/admin'))
    admin.add_link(MenuLink('Logout', url=settings.BASE_PREFIX + '/admin/logout'))
    admin.add_view(User.ModelView(User, db.session))
    admin.add_view(Legislator.ModelView(Legislator, db.session))
    admin.add_view(AdminUser.ModelView(AdminUser, db.session))
    admin.add_view(UserMessageInfo.ModelView(UserMessageInfo, db.session))
    admin.add_view(Message.ModelView(Message, db.session))
    admin.add_view(MessageLegislator.ModelView(MessageLegislator, db.session))
    admin.add_view(Topic.ModelView(Topic, db.session))

    return admin

@register_with_app
def create_app_router(app, csrf):

    app_router = Blueprint('app_router', __name__, template_folder='templates')

    # main user pathway
    app_router.route('/', methods=['GET', 'POST'])(views.index)
    app_router.route('/signup', methods=['GET','POST'])(views.update_user_address)
    app_router.route('/validate/<token>', methods=['GET', 'POST'])(views.update_user_address)
    app_router.route('/confirm_reps/<token>', methods=['GET', 'POST'])(views.confirm_reps)
    app_router.route('/complete/<token>', methods=['GET'])(views.complete)

    # bonus points
    app_router.route('/legislator_index', methods=['GET'])(views.legislator_index)
    app_router.route('/district/<state>/<district>', methods=['GET'])(views.district)

    # reset token
    app_router.route('/new_token/<token>', methods=['GET'])(views.new_token)
    app_router.route('/reset_token', methods=['GET', 'POST'])(views.reset_token)

    # ajax
    app_router.route('/ajax/autofill_address', methods=['POST'])(actions.autofill_address)

    # static pages
    app_router.route('/faq', methods=['GET'])(views.faq)

    # error pages
    @app.errorhandler(404)
    def page_not_found(error):
        return render_template_wctx('404.html'), 404

    @app.errorhandler(500)
    def internal_server(error):
        app.logger.error('Server Error: %s', (error))
        return render_template_wctx('500.html'), 500

    # handlers
    @app.after_request
    def call_after_request_callbacks(response):
        for callback in getattr(g, 'after_request_callbacks', ()):
            callback(response)
        return response

    return app_router

@register_with_app
def create_postmark_router(app, csrf):

    postmark_router = Blueprint('postmark_router', __name__, template_folder='templates')
    postmark_router.route('/postmark/inbound', methods=['POST'])(views.postmark_inbound)

    return postmark_router