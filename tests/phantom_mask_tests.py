import sys
import os
from flask.ext.testing import TestCase
import unittest

sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), os.path.pardir))
os.environ['PHANTOM_ENVIRONMENT'] = 'test'
##########################################################################################

from app import models
from app import phantom_mask
import factories
from tasks import daily
from tasks import monthly
from app.helpers import abs_base_url
from flask import url_for

class phantom_maskTestCase(TestCase):

    def create_app(self):
        app = phantom_mask.config_ext(phantom_mask.create_app())
        app.config['TESTING'] = True
        app.config['PRESERVE_CONTEXT_ON_EXCEPTION'] = False
        return app

    """
    def setUp(self):
        models.db.create_all()


    def tearDown(self):
        models.db.session.remove()
        models.db.drop_all()
    """
    @classmethod
    def setUpClass(cls):
        models.db.create_all()
        daily.import_congresspeople(from_cache=True)
        monthly.import_topics(from_cache=True)

    @classmethod
    def tearDownClass(cls):
        models.db.session.remove()
        models.db.drop_all()

    def test_views__legislator_index(self):
        """

        @return:
        """
        rv = self.client.get(url_for('app_router.legislator_index'))
        assert 'Index of contactable legislators can be found below.' in rv.data

    def test_models__usermessageinfo(self):
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

if __name__ == '__main__':
    unittest.main()