import os

# Default Django Settings

SECRET_KEY = "secret"
DEBUG = True
ALLOWED_HOSTS = ['testserver']
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'tests.test_django'
]
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]
ROOT_URLCONF = 'tests.test_django'
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}
# End of Django Settings

# This section is typically found in wsgi.py or manage.py
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tests.test_django')
import django
django.setup()

# End of Django initialization


# Contents of squealy.py
from squealy.django import DjangoSquealy
from squealy import Resource

resource = Resource("userprofile", queries=[{"queryForObject": "SELECT 1 as id, 'A' as name"}])
squealy = DjangoSquealy(resources={resource.id: resource})

# end of squealy.py

#Contents of urls.py
from django.urls import path
from squealy.django import SqlView
urlpatterns = [
    # Use an application provided squealy object
    path('squealy/userprofile/', SqlView.as_view(resource='userprofile', squealy=squealy)),

    # Use a resource object instead of a string identifier
    path('squealy/alt-userprofile/', SqlView.as_view(resource=resource, squealy=squealy)),

    # Use the default squealy object that loads resources *.resource.yml files under each django app
    path('squealy/questions/', SqlView.as_view(resource='questions')),

    # The same resource should be accessible using the file name
    path('squealy/alt-questions/', SqlView.as_view(resource='questions.resource.yml')),

    # Use the file name instead of the id
    path('squealy/users/', SqlView.as_view(resource='users.resource.yml')),

    # In a subfolder, with the *.yaml extension
    path('squealy/comments/', SqlView.as_view(resource='subfolder/comments.resource.yaml')),
]

# Our Test Cases start from here


import unittest
from django.test import Client
from django.db import connections
from squealy.django import DjangoORMEngine

class DjangoTests(unittest.TestCase):
    def test_django_with_sqlite(self):
        conn = connections['default']        
        engine = DjangoORMEngine(connections['default'])
        table = engine.execute("SELECT 'a' as A, 1 as B where 1 = %s", [1])
        
        self.assertEqual(['A', 'B'], table.columns)
        self.assertEqual([('a', 1)], table.data)

    def test_sqlview(self):
        c = Client()
        response = c.get("/squealy/userprofile/")
        self.assertEqual(response.json(), {'data': {'id': 1, 'name': 'A'}})
        response = c.get("/squealy/alt-userprofile/")
        self.assertEqual(response.json(), {'data': {'id': 1, 'name': 'A'}})

    def test_sqlview_with_default_squealy(self):
        expected_data = [{'id': 1, 'title': 'How to install squealy?', 
                'comments': [
                    {'qid': 1, 'comment': 'What OS?'}, 
                    {'qid': 1, 'comment': 'Ubuntu 18.04'}, 
                    {'qid': 1, 'comment': 'Okay - pip install squealy'}
                ]
            }, {'id': 2, 'title': 'Can Squealy be used in Java?', 
                'comments': [
                    {'qid': 2, 'comment': 'No, only python for now'}, 
                    {'qid': 2, 'comment': 'You can run in docker and call over http from java'}
                ]
            }
        ]

        c = Client()
        response = c.get("/squealy/questions/")
        self.assertEqual(response.json()['data'], expected_data)

        response = c.get("/squealy/alt-questions/")
        self.assertEqual(response.json()['data'], expected_data)

    def test_sqlview_resource_without_explicit_id(self):
        c = Client()
        response = c.get("/squealy/users/")

        self.assertEqual(response.json()['data'], 
            [{'id': 1, 'name': 'sri'}, {'id': 2, 'name': 'anshu'}])

    def test_sqlview_resource_in_subfolder(self):
        c = Client()
        response = c.get("/squealy/comments/")

        self.assertEqual(response.json()['data'], [
            {'id': 1, 'comment': 'This is the first comment'}, 
            {'id': 2, 'comment': 'Nothing spectacular, but this is the second comment'}
        ])