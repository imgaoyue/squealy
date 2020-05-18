from django.db import connections
from django.views import View
from django.http import JsonResponse

from squealy import Squealy, Engine

class DjangoSquealy(Squealy):
    def __init__(self, home_dir):
        self.load_resources(home_dir)
        for name, conn in connections.items():
            self.add_engine(name, DjangoORMEngine(conn))

class DjangoORMEngine(Engine):
    def __init__(self, conn):
        self.conn = conn

    def execute(self, query, bind_params):
        with conn.cursor() as cursor:
            cursor.execute(query, bind_params)
            cols = [col[0] for col in cursor.description]
            rows = cursor.fetchall()
        table = Table(columns=result.keys(), data=[r.values() for r in rows])
        return table

    def execute_for_json(self, query, bind_params):
        'Assume the query returns exacyly 1 row with exactly 1 column, and that cell is a JSON encoded string'
        with conn.cursor() as cursor:
            cursor.execute(query, bind_params)
            row = cursor.fetchone()
            return row[0]

    # TODO: Make this method django connection specific
    def _identify_param_style(self):
        dialect_str = str(type(engine.dialect).__module__).lower()
        if 'sqlite' in dialect_str:
            engine.param_style = 'qmark'
        elif 'oracle' in dialect_str:
            engine.param_style = 'numeric'
        else:
            engine.param_style = 'format'

class SqlView(View):
    def __init__(self, squealy, resource_id):
        self.squealy = squealy
        self.resource = squealy.get_resource(resource_id)

    def build_context(request, *args, **kwargs):
        params = {}
        params.update(request.GET)
        params.update(kwargs)

        return {
            "user": request.user, 
            "params": params
        }

    def get(self, request, *args, **kwargs):
        context = self.build_context(request, *args, **kwargs)
        data = self.resource.process(self.squealy, context)
        return JsonResponse(data)
