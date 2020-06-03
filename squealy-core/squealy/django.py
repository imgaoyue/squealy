import os
from django.apps import apps
from django.conf import settings
from django.db import connections
from django.views import View
from django.http import JsonResponse

from squealy import Squealy, Resource, Engine, Table, SquealyConfigException

class DjangoSquealy(Squealy):
    def __init__(self, snippets=None, resources=None):
        super(DjangoSquealy, self).__init__(snippets=snippets, resources=resources)
        for conn_name in connections:
            self.add_engine(conn_name, DjangoORMEngine(connections[conn_name]))
        
        resource_dirs = []
        for app_config in apps.get_app_configs():
            name = app_config.name
            if name.startswith('django.contrib.') or name in ('rest_framework', ):
                continue
            resource_dirs.append(app_config.path)
        if resource_dirs:
            self.load_objects(resource_dirs)

class DjangoORMEngine(Engine):
    def __init__(self, conn):
        self.conn = conn
        # Django uses %s for bind parameters, across all databases
        self.param_style = 'format'

    def execute(self, query, bind_params):
        with self.conn.cursor() as cursor:
            cursor.execute(query, bind_params)
            cols = [col[0] for col in cursor.description]
            rows = cursor.fetchall()
        table = Table(columns=cols, data=rows)
        return table

    def execute_for_json(self, query, bind_params):
        'Assume the query returns exacyly 1 row with exactly 1 column, and that cell is a JSON encoded string'
        with conn.cursor() as cursor:
            cursor.execute(query, bind_params)
            row = cursor.fetchone()
            return row[0]

def load_default_squealy():
    squealy = DjangoSquealy()
    return squealy

_DEFAULT_SQUEALY = load_default_squealy()

class SqlView(View):
    # squealy and resource_id will be set when SqlView.as_view() is called
    squealy = _DEFAULT_SQUEALY
    resource = None

    def build_context(self, request, *args, **kwargs):
        params = {}
        params.update(request.GET)
        params.update(kwargs)

        return {
            "user": request.user, 
            "params": params
        }

    def get(self, request, *args, **kwargs):
        if not self.resource:
            raise SquealyConfigException('resource is not set, did you forget to pass it in SqlView.as_view(resource=) ?')
        context = self.build_context(request, *args, **kwargs)
        if isinstance(self.resource, Resource):
            resource = self.resource
        else:
            resource = self.squealy.get_resource(self.resource)
        data = resource.process(self.squealy, context)
        return JsonResponse(data)

