from postmark import PMMail
from config import settings
from util import render_without_request
from util import DummyEmail
from helpers import url_for_with_prefix

def apply_admin_filter(func):
    """
    Decorator to check the debug status of the app before sending emails to users.

    @param func: callable defined below
    @return: callable
    """
    def check_for_admin_email(*args, **kwargs):
        pmmail = func(*args, **kwargs)

        if not settings.APP_DEBUG or (settings.APP_DEBUG and args[1].email in settings.ADMIN_EMAILS):
            print 'Sending live email to ' + args[1].email
            return pmmail
        else:
            print 'Debug mode and user not in list of admin emails'
            return DummyEmail(pmmail)
    return check_for_admin_email


class NoReply():

    SENDER_EMAIL = settings.NO_REPLY_EMAIL

    @classmethod
    @apply_admin_filter
    def token_reset(cls, user):
        """


        @return: a python representation of a postmark object
        @rtype: PMMail
        """
        return PMMail(api_key=settings.POSTMARK_API_KEY,
                      sender=cls.SENDER_EMAIL,
                      to=user.email,
                      subject="You've requested to reset your OpenCongress token.",
                      html_body=render_without_request("emails/token_reset.html",
                                                        context={'verification_link': user.tmp_token_link(),
                                                                 'user': user}),
                      track_opens=True
                      )


    @classmethod
    @apply_admin_filter
    def validate_user(cls, user, msg):
        """
        Handles the case of a first time user or a user who needs to renew this contact information.

        @param user: the user to send the email to
        @type user: models.User
        @param veri_link: the verification link to enter in their information
        @type veri_link: string
        @return: a python representation of a postmark object
        @rtype: PMMail
        """

        veri_link = msg.verification_link()


        return PMMail(api_key=settings.POSTMARK_API_KEY,
                      sender=cls.SENDER_EMAIL,
                      to=user.email,
                      subject='Re: ' + msg.subject,
                      html_body=render_without_request("emails/validate_user.html",
                                                        context={'verification_link': veri_link,
                                                                 'user': user}),
                      text_body=render_without_request('emails/validate_user.txt.html',
                                                       context={'verification_link': veri_link,
                                                                 'user': user}),
                      track_opens=True,
                      custom_headers={
                          'In-Reply-To': msg.email_uid,
                          'References': msg.email_uid,
                        }
                      )

    @classmethod
    @apply_admin_filter
    def signup_success(cls, user):
        """

        @param user: the user to send the email to
        @type user: models.User
        @return: a python representation of a postmark object
        @rtype: PMMail
        """

        return PMMail(api_key=settings.POSTMARK_API_KEY,
              sender=cls.SENDER_EMAIL,
              to=user.email,
              subject="You are successfully signed up for OpenCongress email congress.",
              html_body=render_without_request('emails/signup_success.html',
                                               context={'link': user.address_change_link(),
                                                        'user': user})
              )




    @classmethod
    @apply_admin_filter
    def reconfirm_info(cls, user, msg):

        veri_link = msg.verification_link()

        return PMMail(api_key=settings.POSTMARK_API_KEY,
                      sender=cls.SENDER_EMAIL,
                      to=user.email,
                      subject="Complete your email to Congress",
                      html_body=render_without_request("emails/revalidate_user.html",
                                                        context={'verification_link': veri_link,
                                                                 'user': user}),
                      track_opens=True
                      )



    @classmethod
    @apply_admin_filter
    def message_receipt(cls, user, legs, msg):
        """
        Handles the follow-up email for every time a user sends an email message.

        @param user: the user to send the email to
        @type user: models.User
        @param legs: dictionary of different cases of contactability with lists of legislators
        @type legs: dict
        @param veri_link: the verification link if a captcha is required
        @type veri_link: string
        @param rls: the rate limit status
        @type rls: string
        @return: a python representation of a postmark object
        @rtype: PMMail
        """

        rls = msg.status

        subject = {
            None: 'Your message to your representatives will be sent.',
            'free': 'Your message to your representatives is schedule to be sent.',
            'captcha': "You must solve a captcha to complete your message to congress",
            'g_captcha': 'You must complete your message to Congress.',
            'block': 'Unable to send your message to congress at this time.'
        }.get(rls)

        return PMMail(api_key=settings.POSTMARK_API_KEY,
                      sender=cls.SENDER_EMAIL,
                      to=user.email,
                      subject=subject,
                      html_body=render_without_request("emails/message_receipt.html",
                                                       context={'legislators': legs,
                                                                'msg': msg,
                                                                'user': user,
                                                                'rls': rls}),
                      track_opens=True
                      )


    @classmethod
    @apply_admin_filter
    def send_status(cls, user, msg_legs):
        """
        Handles the case where phantom of the capitol is unable to send a message to a particular
        legislator. Notifies the user of such and includes the contact form URL in the body.

        @param user: the user to send the email to
        @type user: models.User
        @param leg: the legislator that was uncontactable
        @type leg: models.Legislator
        @return: a python representation of a postmark object
        @rtype: PMMail
        """

        send_statuses = {True: [], False: []}
        for ml in msg_legs:
            send_statuses[ml.get_send_status()['status'] == 'success'].append(ml.legislator)

        if len(send_statuses[False]) > 0:
            subject = 'There were errors processing your recent message to congress.'
        else:
            subject = 'Your recent message to congress has successfully sent.'

        return PMMail(api_key=settings.POSTMARK_API_KEY,
                      sender=cls.SENDER_EMAIL,
                      to=user.email,
                      subject=subject,
                      html_body=render_without_request("emails/send_status.html",
                                                        context={'legislators': send_statuses,
                                                                 'user': user}),
                      track_opens=True
                      )

    @classmethod
    @apply_admin_filter
    def successfully_reset_token(cls, user):
        """
        Handles the case of notifying a user when they've changed their address information.

        @param user: the user to send the email to
        @type user: models.User
        @param umi: user message information instance
        @type umi: models.UserMessageInfo
        @return: a python representation of a postmark object
        @rtype: PMMail
        """
        link = user.token.link()

        return PMMail(api_key=settings.POSTMARK_API_KEY,
                      sender=cls.SENDER_EMAIL,
                      to=user.email,
                      subject='Your OpenCongress email token has been successfully reset.',
                      html_body=render_without_request('emails/successfully_reset_token.html',
                                                       context={'user': user, 'link': link})
                      )


    @classmethod
    @apply_admin_filter
    def address_changed(cls, user):
        """
        Handles the case of notifying a user when they've changed their address information.

        @param user: the user to send the email to
        @type user: models.User
        @return: a python representation of a postmark object
        @rtype: PMMail
        """

        return PMMail(api_key=settings.POSTMARK_API_KEY,
                      sender=cls.SENDER_EMAIL,
                      to=user.email,
                      subject='Your OpenCongress contact information has changed.',
                      html_body=render_without_request('emails/address_changed.html',
                                                       context={'link': user.address_change_link(),
                                                                'user': user,
                                                                'moc': user.default_info.members_of_congress})
                      )
