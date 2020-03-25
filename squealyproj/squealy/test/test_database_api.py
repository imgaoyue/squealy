from django.conf import settings

from .test_base_file import BaseTestCase


class DatabaseApiTestCase(BaseTestCase):

    def setUp(self):
        BaseTestCase.create_mock_user(self)
        BaseTestCase.create_mock_client(self)

    def test_exception_in_database_api(self):
        """
            If no database is present in settings, throw Exception
        """
        response = self.client.get('/databases/')
        json_response = response.json()
        self.assertEqual(json_response, {u'detail': u'No databases defined'})
