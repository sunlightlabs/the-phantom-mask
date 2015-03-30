from postmark import PMMail
from config import settings
from util import render_without_request

class NoReply():

    SENDER_EMAIL = settings.NO_REPLY_EMAIL

    @staticmethod
    def apply_admin_filter(func):
        """
        Decorator to check the debug status of the app before sending emails to users.

        @param func: callable defined below
        @return: callable
        """
        def check_for_admin_email(*args, **kwargs):
            if not settings.APP_DEBUG or (settings.APP_DEBUG and args[1] in settings.ADMIN_EMAILS):
                print str(settings.APP_DEBUG)
                print str(args[1] in settings.ADMIN_EMAILS)
                return func(*args, **kwargs)
        return check_for_admin_email

    @classmethod
    @apply_admin_filter.__func__
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
    @apply_admin_filter.__func__
    def uncontactable(cls, to, legs):
        return PMMail(api_key=settings.POSTMARK_API_KEY,
                      sender=cls.SENDER_EMAIL,
                      to=to,
                      subject='Uncontactable or unknown email address for representative or senator',
                      html_body=render_without_request('emails/uncontactable.html',
                                                        context={})
                      )