import sys
import os
from flask.ext.testing import TestCase
import unittest

sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), os.path.pardir))
import phantom_mask
import models
import factories
from tasks import daily

class phantom_maskTestCase(TestCase):

    SQLALCHEMY_DATABASE_URI = "sqlite://"
    TESTING = True

    def create_app(self):
        app = phantom_mask.app
        app.config['TESTING'] = self.TESTING
        app.config['PRESERVE_CONTEXT_ON_EXCEPTION'] = False
        return app

    def setUp(self):
        models.db.create_all()

    def tearDown(self):
        models.db.session.remove()
        models.db.drop_all()

    def test_views__legislator_index(self):
        """

        @return:
        """
        rv = self.client.get('/legislator_index/')
        assert 'Index of contactable legislators can be found below.' in rv.data

    def test_models__usermessageinfo(self):
        user = factories.user()
        assert user.id is not None
        umi = factories.user_message_info(user=user)
        assert umi.id is not None
        umi.confirmed = True
        models.db.session.commit()
        assert umi.confirmed is True

        daily.import_congresspeople()

        moc = umi.members_of_congress

        for leg in moc:
            assert leg.state == umi.state


if __name__ == '__main__':
    unittest.main()