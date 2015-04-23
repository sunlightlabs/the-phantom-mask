import sys
import os
from flask.ext.testing import TestCase
import unittest

sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), os.path.pardir))
os.environ['PHANTOM_ENVIRONMENT'] = 'test'
##########################################################################################

from app import models, phantom_mask, emailer
import factories
from tasks import daily, monthly
from flask import url_for
import json

class phantom_maskTestCase(TestCase):

    def create_app(self):
        app = phantom_mask.config_ext(phantom_mask.create_app())
        app.config['TESTING'] = True
        app.config['PRESERVE_CONTEXT_ON_EXCEPTION'] = False
        app.config['CSRF_ENABLED'] = False
        app.config['WTF_CSRF_ENABLED'] = False
        return app

    @classmethod
    def setUpClass(cls):
        models.db.create_all()
        daily.import_congresspeople(from_cache=True)
        monthly.import_topics(from_cache=True)
        user = factories.user(email='test@example.com')
        umi = factories.user_message_info(user=user)
        msg = factories.message(umi=umi)
        legs = models.Legislator.query.all()
        msg_leg = factories.message_legislator(msg, legs[0], send_status='{"status": "success"}', sent=True)
        msg_leg = factories.message_legislator(msg, legs[1], send_status='{"status": "error"}', sent=False)
        msg_leg = factories.message_legislator(msg, legs[2], send_status='{"status": "failure"}', sent=False)

    @classmethod
    def tearDownClass(cls):
        models.db.session.remove()
        models.db.drop_all()

    ########## app/views.py ##########

    def test_views__legislator_index(self):
        rv = self.client.get(url_for('app_router.legislator_index'))
        assert 'Index of contactable legislators can be found below.' in rv.data


    def test_views__district(self):
        rv = self.client.get(url_for('app_router.district', state='NC', district='3'))
        assert 'Here are your Senators and Representative.' in rv.data


    def test_views__reset_token(self):
        rv = self.client.get(url_for('app_router.reset_token'))
        assert "Input your email address below" in rv.data
        rv = self.client.post(url_for('app_router.reset_token'), data={'email': 'test@example.com'})
        assert 'Your token has been reset.' in rv.data

    def test_views__new_token(self):
        user = models.User.query.filter_by(email='test@example.com').first()
        user.create_tmp_token()
        rv = self.client.get(url_for('app_router.new_token', token=user.tmp_token), follow_redirects=True)
        assert "Please fill out the form below." in rv.data

    ########## app/models.py ##########

    def test_models__user_message_info(self):
        user = factories.user()
        assert user.id is not None
        umi = factories.user_message_info(user=user)
        assert umi.id is not None
        umi.confirmed = True
        models.db.session.commit()
        assert umi.confirmed is True

        moc = umi.members_of_congress

        for leg in moc:
            assert leg.state == umi.state

    ########## app/emailer.py ##########

    def test_emailer__token_reset(self):
        user = models.User.query.first()
        user.create_tmp_token()
        pmmail = emailer.NoReply.token_reset(user)
        assert pmmail.subject == "You've requested to reset your OpenCongress token."
        assert "You've requested to reset your token." in pmmail.html_body
        assert user.verification_link() in pmmail.html_body


    def test_emailer__validate_user(self):
        msg = models.Message.query.first()
        pmmail = emailer.NoReply.validate_user(msg.user_message_info.user, msg)
        assert pmmail.subject == 'Complete your email to Congress'
        assert 'Hello user.' in pmmail.html_body
        assert msg.verification_link() in pmmail.html_body


    def test_emailer__message_receipt(self):
        user = models.User.query.first()
        msg = factories.message(umi=user.default_info)
        msg.kill_link()
        to_list = ['Rep.Cicilline@opencongress.org', 'Rep.Aderholt@opencongress.org', 'Rep.qqwe@opencongress.org']
        legs = models.Legislator.get_leg_buckets_from_emails(user.default_info.members_of_congress, to_list)
        pmmail = emailer.NoReply.message_receipt(user, legs, msg)
        assert pmmail.subject == 'Your message to your representatives will be sent.'
        assert 'Your message is schedule to be sent to the following legislators:' in pmmail.html_body
        assert 'because our records indicate that you do not reside in their district' in pmmail.html_body
        assert 'The following emails are unrecognizable by our system' in pmmail.html_body
        assert user.verification_link() in pmmail.html_body


    def test_emailer__send_status(self):
        user = models.User.query.filter_by(email='test@example.com').first()
        msg = user.messages().first()
        pmmail = emailer.NoReply.send_status(user, msg.to_legislators)
        assert 'Unfortunate we were unable to send your message' in pmmail.html_body
        assert 'Your message was successfully sent to the following members of congress' in pmmail.html_body
        assert 'There were errors processing your recent message to congress' in pmmail.subject


    def test_emailer__address_changed(self):
        user = models.User.query.first()
        user.create_tmp_token()
        pmmail = emailer.NoReply.address_changed(user)
        assert pmmail.subject == 'Your OpenCongress contact information has changed.'
        assert 'Your address has recently been changed.' in pmmail.html_body
        assert user.tmp_token_link() in pmmail.html_body


if __name__ == '__main__':
    unittest.main()