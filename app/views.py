import traceback
import json
import urllib2
import urllib
import inspect
from flask import jsonify, redirect, request, url_for, abort, g
from postmark_inbound import PostmarkInbound
from lib.usps import CODE_TO_STATE
import emailer
import forms
import flask_login
from config import settings
from phantom_mask import db
from flask.ext.login import login_user, logout_user, login_required, current_user
from sqlalchemy import func
from models import Legislator, Message, MessageLegislator, Token, User, AdminUser, UserMessageInfo, db_first_or_create, db_add_and_commit
from helpers import render_template_wctx, convert_token, url_for_with_prefix, append_get_params, app_router_path
from flask_admin import expose
import flask_admin as admin
from flask.ext.login import LoginManager
from sqlalchemy import and_, not_
from functools import wraps
import datetime

login_manager = LoginManager()

class MyAdminIndexView(admin.AdminIndexView):

    @login_manager.user_loader
    def load_admin(adminid):
        return AdminUser.query.get(int(adminid))

    def is_accessible(self):
        return flask_login.current_user.is_authenticated()

    def _handle_view(self, name, **kwargs):
        if name != 'login' and not self.is_accessible():
            return redirect(url_for_with_prefix('admin.login', next=request.url))

    @expose('/')
    def index(self):

        user_analytics = User.Analytics()

        user_count = user_analytics.total_count()
        message_count = Message.query.count()
        message_leg_count = MessageLegislator.query.filter_by(sent=None).count()
        users_w_districts_count = user_analytics.users_with_verified_districts()


        context = {
            'users_w_districts_percent': '{:.2%}'.format(float(users_w_districts_count) / float(user_count)),
            'new_users_growth_rate': '{:.2%}'.format(user_analytics.growth_rate(30)),
            'new_users_last_30_count': user_analytics.new_last_n_days(30),
            'user_count': user_count,
            'new_users_today_count': user_analytics.new_today(),
            'message_count': message_count,
            'message_leg_count': message_leg_count,
            'users_w_districts_count': users_w_districts_count,
            'avg_msg_per_user': float(message_count) / float(user_count),
            'total_msg_to_legs': MessageLegislator.query.count(),
            'unsent_msg_to_legs': MessageLegislator.query.filter_by(sent=None).count(),
            'sent_msg_to_legs': MessageLegislator.query.filter_by(sent=True).count(),
            'error_msg_to_legs': MessageLegislator.query.filter_by(sent=False).count()
        }

        return self.render('admin/index.html', context=context)


    @expose('/login', methods=['GET', 'POST'])
    def login(self):
        form = forms.LoginForm(request.form, url_for_with_prefix('.login'))
        if request.method == 'POST':
            admin = form.validate_credentials()
            if admin: login_user(admin)
            return redirect(url_for_with_prefix('.index'))
        return render_template_wctx('pages/admin_login.html', context={'form': form})


    @expose('/logout', methods=['GET', 'POST'])
    def logout(self):
        logout_user()
        return redirect(url_for_with_prefix('admin.login'))


def index():
    return render_template_wctx('pages/index.html', context={})


def faq():
    return render_template_wctx('pages/static/faq.html', context={})


def after_this_request(f):
    if not hasattr(g, 'after_request_callbacks'):
        g.after_request_callbacks = []
    g.after_request_callbacks.append(f)
    return f


def resolve_token(viewfunc):

    @wraps(viewfunc)
    def token_or_redirect(**kwargs):
        token = kwargs.get('token', '')
        msg, umi, user = Token.convert_token(token)
        if user is None:
            # TODO where to redirect?
            return redirect(url_for_with_prefix('app_router.reset_token'))
        else:
            if msg is not None:
                if msg.is_already_sent() and viewfunc.__name__ is not 'message_sent':
                    return redirect(url_for_with_prefix('app_router.message_sent', token=token))
                elif not msg.is_already_sent() and user.default_info.accept_tos and viewfunc.__name__ not in ['confirm_reps', 'message_sent']:
                    return redirect(url_for_with_prefix('app_router.confirm_reps', token=token))

            kwargs.update({'msg': msg, 'umi': umi, 'user': user})
            return viewfunc(**kwargs)

    return token_or_redirect


def district(state, district):
    legs = Legislator.members_for_state_and_district(state, district)

    context = {
        'legislators': legs,
        'humanized_district': Legislator.humanized_district(state, district),
        'geojson_url': Legislator.get_district_geojson_url(state, district)
    }

    return render_template_wctx('pages/congressional_district.html', context=context)

def legislator_index(**kwargs):

    context = {
        'legislators': Legislator.query.all(),
        'states': CODE_TO_STATE
    }

    return render_template_wctx('pages/legislator_index.html', context=context)


def reset_token():
    """
    View to allow user to reset their token if it becomes compromised, they can't find
    the link in their email, or otherwise.
    """

    form = forms.TokenResetForm(request.form, url_for_with_prefix('app_router.' + inspect.stack()[0][3]))

    context = {
        'form': form
    }

    if form.validate_on_submit():
        context['success'] = True
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            user.create_tmp_token()
            emailer.NoReply.token_reset(user).send()

    return render_template_wctx('pages/reset_token.html', context=context)

@resolve_token
def confirm_with_recaptcha(token='', msg=None, umi=None, user=None):
    form = forms.RecaptchaForm(request.form, app_router_path(inspect.stack()[0][3], token=token))

    context = {
        'form': form
    }

    if form.validate_on_submit():
        msg.free_link()
        process_inbound_message(user, umi, msg, send_email=True)
        context['legislators'] = umi.members_of_congress
        return render_template_wctx('pages/message_sent.html', context=context)

    return render_template_wctx('pages/confirm_with_recaptcha.html', context=context)


def new_token(token=''):

    user = User.query.filter_by(tmp_token=token).first()

    if user is not None:
        user.create_tmp_token()
        token = user.token.reset()
        emailer.NoReply.successfully_reset_token(user).send()
        return redirect(url_for_with_prefix('app_router.update_user_address', token=token))
    else:
        return 'No user exists for specified token.'

@resolve_token
def message_sent(token='', msg=None, umi=None, user=None):

    context = {
        'umi': umi,
        'legislators': umi.members_of_congress,
        'msg_legislators': msg.get_legislators(),
        'msg': msg
    }

    return render_template_wctx('pages/message_sent.html', context=context)


@resolve_token
def confirm_reps(token='', msg=None, umi=None, user=None):
    """
    Confirm members of congress and submit message (if message present)

    @param token: token to identify the user / message
    @type token: string
    @return:
    @rtype:
    """

    form = forms.MessageForm(request.form, append_get_params(url_for_with_prefix('app_router.' + inspect.stack()[0][3], token=token)))

    moc = umi.members_of_congress

    context = {
        'form': form,
        'msg': msg,
        'user': user,
        'umi': umi,
        'legislators': moc
    }

    if msg is not None and request.method == 'POST' and form.validate() and request.form.getlist('legislator_choices[]'):
        if not request.form.get('donotsend', False):
            legs = [moc[int(i)] for i in request.form.getlist('legislator_choices[]')]
            msg.queue_to_send(legs)
            emailer.NoReply.message_queued(user, legs, msg).send()
        return redirect(url_for_with_prefix('app_router.message_sent', token=token))
    else:
        if msg is not None:
            form.populate_data_from_message(msg)
            context['legs_buckets'] = Legislator.get_leg_buckets_from_emails(umi.members_of_congress, json.loads(msg.to_originally))
        return render_template_wctx('pages/confirm_reps.html', context=context)


@resolve_token
def update_user_address(token='', msg=None, umi=None, user=None):

    form = forms.RegistrationForm(request.form, app_router_path(inspect.stack()[0][3], token=token))

    context = {
        'form': form,
        'verification_token': token,
        'msg_email': user.email,
        'umi': umi,
        'msg': msg
    }

    if request.method == 'POST':
        if form.validate_and_save_to_db(user, msg=msg):
            district = umi.determine_district(force=True)
            if district is None:
                context['district_error'] = True
            else:
                if msg is None:
                    token = user.token.reset()
                    emailer.NoReply.address_changed(user).send()
                else:
                    emailer.NoReply.signup_success(user, msg).send()
                return redirect(url_for_with_prefix('app_router.confirm_reps', token=token))

    return render_template_wctx("pages/update_user_address.html", context=context)


def process_inbound_message(user, umi, msg, send_email=False):

    legs = Legislator.get_leg_buckets_from_emails(umi.members_of_congress, json.loads(msg.to_originally))
    msg.set_legislators(legs['contactable'])

    if msg.has_legislators() and msg.is_free_to_send():
        emailer.NoReply.message_queued(user, legs['contactable'], msg).send()
        msg.queue_to_send()
    if legs['does_not_represent'] or legs['non_existent']:
        emailer.NoReply.message_undeliverable(user, legs, msg).send()

    return jsonify({'status': 'success'})


def postmark_inbound():
    """
    View to handle inbound postmark e-mails.

    @return:
    """
    try:
        # parse inbound postmark JSON
        inbound = PostmarkInbound(json=request.get_data())

        # create or get the user and his default information
        user = db_first_or_create(User, email=inbound.sender()['Email'].lower())
        umi = db_first_or_create(UserMessageInfo, user_id=user.id, default=True)

        if 'Headers' in inbound.source and inbound.headers('Message-ID') is not None:
            msg_id = inbound.headers('Message-ID')
        else:
            msg_id = inbound.message_id()

        # check if message exists already first
        if Message.query.filter_by(email_uid=inbound.message_id()).first() is None:

            new_msg = Message(created_at=inbound.send_date(),
                              to_originally=json.dumps([r['Email'].lower() for r in inbound.to()]),
                              subject=inbound.subject(),
                              msgbody=inbound.text_body(),
                              email_uid=msg_id,
                              user_message_info_id=umi.id)
            db_add_and_commit(new_msg)

            # first time user or it has been a long time since they've updated their address info
            if umi.should_update_address_info():
                emailer.NoReply.validate_user(user, new_msg).send()
                return jsonify({'status': 'user must accept tos / update their address info'})
            else:
                new_msg.update_status()
                return process_inbound_message(user, umi, new_msg, send_email=True)
        else:
            return jsonify({'status': 'message already received'})
    except:
        print traceback.format_exc()
        return "Unable to parse postmark message.", 500