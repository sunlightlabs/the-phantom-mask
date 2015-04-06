from postmark import PMMail
from config import settings
from util import render_without_request

def apply_admin_filter(func):
    """
    Decorator to check the debug status of the app before sending emails to users.

    @param func: callable defined below
    @return: callable
    """
    def check_for_admin_email(*args, **kwargs):
        pmmail = func(*args, **kwargs)

        if not settings.APP_DEBUG or (settings.APP_DEBUG and args[1] in settings.ADMIN_EMAILS):
            return pmmail
        else:
            print "***Debug Mode*** Message below WILL NOT be sent to: " + args[1]
            print pmmail.html_body
    return check_for_admin_email


class NoReply():

    SENDER_EMAIL = settings.NO_REPLY_EMAIL

    @classmethod
    @apply_admin_filter
    def validate_user(cls, to, veri_link):
        return PMMail(api_key=settings.POSTMARK_API_KEY,
                      sender=cls.SENDER_EMAIL,
                      to=to,
                      subject="Complete your email to Congress",
                      html_body=render_without_request("emails/validate_user.html",
                                                        context={'verification_link': veri_link}),
                      track_opens=True
                      )

    @classmethod
    @apply_admin_filter
    def message_receipt(cls, to, legs, veri_link):
        unable_count = len(legs[False])
        able_count = len(legs[True])
        if unable_count == 0:
            subject = 'Your message to Congress has been sent'
        elif unable_count > 0 and able_count > 0:
            subject = 'Your message to Congress has been sent to some recipients...'
        else:
            subject = 'Your message could not be sent to any recipient.'

        return PMMail(api_key=settings.POSTMARK_API_KEY,
                      sender=cls.SENDER_EMAIL,
                      to=to,
                      subject=subject,
                      html_body=render_without_request("emails/message_receipt.html",
                                                        context={'verification_link': veri_link,
                                                                 'legislators': legs}),
                      track_opens=True
                      )



    @classmethod
    @apply_admin_filter
    def complete_message(cls, to, legs, veri_link):
        return PMMail(api_key=settings.POSTMARK_API_KEY,
                      sender=cls.SENDER_EMAIL,
                      to=to,
                      subject="Complete your message to Congress",
                      html_body=render_without_request("emails/complete_message.html",
                                                context={'legs': legs,
                                                         'verification_link': veri_link}),
                      track_opens=True
                      )

    @classmethod
    @apply_admin_filter
    def uncontactable(cls, to, legs):
        return PMMail(api_key=settings.POSTMARK_API_KEY,
                      sender=cls.SENDER_EMAIL,
                      to=to,
                      subject='Uncontactable or unknown email address for representative or senator',
                      html_body=render_without_request('emails/uncontactable.html',
                                                        context={})
                      )