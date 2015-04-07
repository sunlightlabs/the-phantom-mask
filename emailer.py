from postmark import PMMail
from config import settings
from util import render_without_request
from util import DummyEmail

def apply_admin_filter(func):
    """
    Decorator to check the debug status of the app before sending emails to users.

    @param func: callable defined below
    @return: callable
    """
    def check_for_admin_email(*args, **kwargs):
        pmmail = func(*args, **kwargs)

        if not settings.APP_DEBUG or (settings.APP_DEBUG and args[1] in settings.ADMIN_EMAILS):
            print 'In debug mode and user is in list of admin emails.'
            return pmmail
        else:
            print 'Debug mode user not in list of admin emails'
            #print "***Debug Mode*** Message below WILL NOT be sent to: " + args[1]
            #print pmmail.html_body
            return DummyEmail()
    return check_for_admin_email


class NoReply():

    SENDER_EMAIL = settings.NO_REPLY_EMAIL

    @classmethod
    @apply_admin_filter
    def validate_user(cls, user_email, veri_link):
        """
        Handles the case of a first time user or a user who needs to renew this contact infomration.

        @param user_email: the email of the user
        @type user_email: string
        @param veri_link: the verification link to enter in their information
        @type veri_link: string
        @return: a python representation of a postmark object
        @rtype: PMMail
        """
        return PMMail(api_key=settings.POSTMARK_API_KEY,
                      sender=cls.SENDER_EMAIL,
                      to=user_email,
                      subject="Complete your email to Congress",
                      html_body=render_without_request("emails/validate_user.html",
                                                        context={'verification_link': veri_link}),
                      track_opens=True
                      )


    @classmethod
    @apply_admin_filter
    def message_receipt(cls, user_email, legs, veri_link, rls):
        """
        Handles the follow-up email for every time a user sends an email message.

        @param user_email: the email of the user
        @type user_email: string
        @param legs: dictionary of different cases of contactability with lists of legislators
        @type legs: dict
        @param veri_link: the verification link if a captcha is required
        @type veri_link: string
        @param rls: the rate limit status
        @type rls: string
        @return: a python representation of a postmark object
        @rtype: PMMail
        """

        subject = {
            'free': 'Your message to members of Congress will be sent.',
            'captcha': 'You must complete your message to Congress.',
            'block': 'Unable to send your message to congress at this time.'
        }.get(rls)

        return PMMail(api_key=settings.POSTMARK_API_KEY,
                      sender=cls.SENDER_EMAIL,
                      to=user_email,
                      subject=subject,
                      html_body=render_without_request("emails/message_receipt.html",
                                                       context={'verification_link': veri_link,
                                                                'legislators': legs,
                                                                'rls': rls}),
                      track_opens=True
                      )


    @classmethod
    @apply_admin_filter
    def unable_to_send(cls, user_email, leg):
        """
        Handles the case where phantom of the capitol is unable to send a message to a particular
        legislator. Notifies the user of such and includes the contact form URL in the body.

        @param user_email: the user email address to send to
        @type user_email: string
        @param leg: the legislator that was uncontactable
        @type leg: models.Legislator
        @return: a python representation of a postmark object
        @rtype: PMMail
        """

        return PMMail(api_key=settings.POSTMARK_API_KEY,
                      sender=cls.SENDER_EMAIL,
                      to=user_email,
                      subject='Unable to send your message to ' + leg.title_and_last_name(),
                      html_body=render_without_request("emails/unable_to_send.html",
                                                        context={'legislator': leg}),
                      track_opens=True
                      )


    @classmethod
    @apply_admin_filter
    def address_changed(cls, user_email, umi):
        """
        Handles the case of notifying a user when they've changed their address information.

        @param user_email: the user email address to send to
        @type user_email: string
        @param umi: user message information instance
        @type umi: models.UserMessageInfo
        @return: a python representation of a postmark object
        @rtype: PMMail
        """

        return PMMail(api_key=settings.POSTMARK_API_KEY,
                      sender=cls.SENDER_EMAIL,
                      to=user_email,
                      subject='Your OpenCongress contact information has changed.',
                      html_body=render_without_request('emails/address_changed.html',
                                                       context={'umi': umi})
                      )