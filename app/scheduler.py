from celery import Celery
import emailer
from config import settings

cel = Celery('queue', backend=settings.CELERY_BACKEND, broker=settings.CELERY_BROKER)

@cel.task(bind=True, max_retries=settings.CELERY_MAX_RETRIES, default_retry_delay=settings.CELERY_RETRY_DELAY)
def send_to_phantom_of_the_capitol(self, msg_id, force=False):
    """
    Attempts to send the message to various legislators and notifies the user via email

    @param msg_id: ID of message
    @type msg_id: int
    @return:
    @rtype:
    """
    if not settings.APP_DEBUG or force:
        from models import Message
        msg = Message.query.filter_by(id=msg_id).first()
        msg.send()
        if msg.get_send_status() == 'sent' or self.request.retries >= self.max_retries:
            emailer.NoReply.send_status(msg.user_message_info.user, msg.to_legislators).send()
        else:
            raise self.retry(Exception)