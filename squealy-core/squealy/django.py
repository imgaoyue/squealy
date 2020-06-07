import os
from django.apps import apps
from django.conf import settings
from django.db import connections
from django.views import View
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator

import logging
from squealy import Squealy, Resource, Engine, Table, SquealyConfigException

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

class DjangoSquealy(Squealy):
    def __init__(self, snippets=None, resources=None):
        super(DjangoSquealy, self).__init__(snippets=snippets, resources=resources)
        for conn_name in connections:
            self.add_engine(conn_name, DjangoORMEngine(conn_name))
        
        resource_dirs = []
        for app_config in apps.get_app_configs():
            name = app_config.name
            if name.startswith('django.contrib.') or name in ('rest_framework', ):
                continue
            resource_dirs.append(app_config.path)
        if resource_dirs:
            logger.info("Loading resource files from these directories - %s", resource_dirs)
            self.load_objects(resource_dirs)
        else:
            logger.warn("Did not find any directories to load resources!")

class DjangoORMEngine(Engine):
    def __init__(self, conn_name):
        self.conn_name = conn_name
        # Django uses %s for bind parameters, across all databases
        self.param_style = 'format'

    def execute(self, query, bind_params):
        with connections[self.conn_name].cursor() as cursor:
            cursor.execute(query, bind_params)
            cols = [col[0] for col in cursor.description]
            rows = cursor.fetchall()
        table = Table(columns=cols, data=rows)
        return table

def load_default_squealy():
    squealy = DjangoSquealy()
    return squealy

_DEFAULT_SQUEALY = load_default_squealy()

class AnonymousSqlView(View):
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

@method_decorator(login_required, name='dispatch')
class SqlView(AnonymousSqlView):
    pass