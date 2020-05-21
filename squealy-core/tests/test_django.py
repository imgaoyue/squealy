import unittest
import os

from squealy.django import DjangoSquealy, DjangoORMEngine, SqlView

# We want to test Django, but it is too painful to install the complete Django project
# To simplify, this file is a valid settings.py and urls.py file 
# With this module, we are able to load Django connections and perform our testing

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

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tests.test_django')
import django
django.setup()

# This is the contents of application specific squealy.py
from squealy.django import DjangoSquealy
from squealy import Resource

resource = Resource("userprofile", queries=[{"isRoot": True, "queryForObject": "SELECT 1 as id, 'A' as name"}])
squealy = DjangoSquealy(resources={resource.id: resource})

# This is the contents of urls.py
# from django.http import JsonResponse
# from django.views import View
# class MyView(View):
#     def get(self, request):
#         return JsonResponse({"foo": "bar"})

from django.urls import path

urlpatterns = [
    path('squealy/sqlite/', SqlView.as_view(resource_id='userprofile', squealy=squealy))
]

class DjangoTests(unittest.TestCase):
        
    def test_django_with_sqlite(self):
        from django.db import connections
        conn = connections['default']
        
        engine = DjangoORMEngine(connections['default'])
        table = engine.execute("SELECT 'a' as A, 1 as B where 1 = %s", [1])
        
        self.assertEqual(['A', 'B'], table.columns)
        self.assertEqual([('a', 1)], table.data)

    def test_sqlview(self):
        from django.test import Client
        c = Client()
        response = c.get("/squealy/sqlite/")
        self.assertEqual(response.json(), {'data': {'id': 1, 'name': 'A'}})
