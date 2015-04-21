from config import settings
from models import Message, User
from flask import render_template, url_for
from sqlalchemy import and_, not_
import urllib

def abs_base_url():
    return settings.BASE_URL + settings.BASE_PREFIX

def url_for_with_prefix(endpoint, **values):
    return settings.BASE_PREFIX + url_for(endpoint, **values)

def append_get_params(url, **kwargs):
    return url + '?' + urllib.urlencode(kwargs)

def app_router_path(func_name, token, email, **kwargs):
    return append_get_params(url_for_with_prefix('app_router.' + func_name, token=token), email=email)


def render_template_wctx(template_name_or_list, **context):
    """
    Wrapper for flask method for rendering a template. Adds additional app-specific context.

    @param template_name_or_list: name of template to render
    @type template_name_or_list: string or list[string]
    @param context: keyword arguments to pass into template to render
    @type context: dict
    @return: the rendered template
    @rtype:
    """

    if 'context' not in context:
        context['context'] = {}
    if 'base_url' not in context['context']:
        context['context']['base_url'] = settings.BASE_URL
    if 'support_email' not in context['context']:
        context['context']['support_email'] = settings.SUPPORT_EMAIL

    return render_template(template_name_or_list, **context)


def convert_token(token, email_param):
    """
    Converts the URL token to corresponding message, user message info, and user.
    The token can be for Messages or for a User wanting to change his address information.

    @param token: string in url to convert to apprio
    @type token: string
    @param email_param: email GET parameter in url
    @type email_param: string
    @return: tuple of corresponding,
    @rtype: (models.Message, models.UserMessageInfo, models.User)
    """

    msg = Message.query.filter(and_(Message.verification_token==token, not_(Message.link_status.is_(None)))).first()
    if msg is not None and msg.user_message_info.user.email == email_param:
        umi = msg.user_message_info
        user = umi.user
        return msg, umi, user

    user = User.query.filter_by(address_change_token=token, email=email_param).first()
    if user is not None and user.email == email_param:
        return None, user.default_info, user

    return None, None, None