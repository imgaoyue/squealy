import os

# We want to test Django, but it is too painful to install the complete Django project
# To simplify, this file is a valid settings.py and urls.py file 
# With this module, we are able to load Django connections and perform our testing


SQUEALY_HOME_DIR = os.path.abspath(os.path.dirname(__file__))
SECRET_KEY='secret'
DEBUG=True
ALLOWED_HOSTS = ['testserver']
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
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

resource = Resource("userprofile", queries=[{"isRoot": True, "queryForObject": "SELECT 1 as id, 'A' as name"}])
squealy = DjangoSquealy(resources={resource.id: resource})

# end of squealy.py

# Contents of urls.py
from django.urls import path
from squealy.django import SqlView
urlpatterns = [
    # Use an application provided squealy object
    path('squealy/userprofile/', SqlView.as_view(resource_id='userprofile', squealy=squealy)),

    # Use the default squealy object that loads resources from home dir
    path('squealy/questions/', SqlView.as_view(resource_id='questions')),
]


# Our Test Cases start from here

import unittest
from squealy.django import DjangoSquealy, DjangoORMEngine, SqlView
from django.test import Client
from django.db import connections

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

    def test_sqlview_with_default_squealy(self):
        c = Client()
        response = c.get("/squealy/questions/")

        self.assertEqual(response.json()['data'], 
            [{'id': 1, 'title': 'How to install squealy?', 
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
        ])