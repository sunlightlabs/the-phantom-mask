from postmark import PMMail
from config import settings
from flask import render_template

def apply_admin_filter(func):
    def check_for_admin_email(*args, **kwargs):
        if not settings.APP_DEBUG or (settings.APP_DEBUG and args[0].sender()['Email'] in settings.ADMIN_EMAILS):
            return func(*args, **kwargs)
    return check_for_admin_email

@apply_admin_filter
def complete_message(inbound, legs, new_msg):
    return PMMail(api_key=settings.POSTMARK_API_KEY,
                  sender="noreply@opencongress.org",
                  to=inbound.sender()['Email'],
                  subject="Complete your message to Congress",
                  html_body=render_template("emails/complete_message.html",
                                            context={'legs':legs,
                                                     'verification_link': new_msg.verification_link()}),
                  track_opens=True
                  )

@apply_admin_filter
def uncontactable(inbound, legs):
    return PMMail(api_key=settings.POSTMARK_API_KEY,
                  sender='noreply@opencongress.org',
                  to=inbound.sender()['Email'],
                  subject='Uncontactable or unknown email address for representative or senator',
                  html_body=render_template('emails/uncontactable.html',
                                            context={})
                  )