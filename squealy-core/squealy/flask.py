from flask import request, current_app, jsonify
from flask.views import MethodView
from sqlalchemy import create_engine
from squealy import Squealy, Engine, Table, SquealyConfigException

class FlaskSquealy(Squealy):
    def __init__(self, app, home_dir=None, snippets=None, resources=None):
        super(FlaskSquealy, self).__init__(snippets=snippets, resources=resources)
        if home_dir:
            self.load_resources(home_dir)
        self._load_engines(app)

        # Store squealy under app['extensions'] so we can later retrieve it
        if not hasattr(app, 'extensions'):
            app.extensions = {}
        app.extensions['squealy'] = self
    
    def _load_engines(self, app):
        if 'SQLALCHEMY_DATABASE_URI' in app.config:
            engine = create_engine(self.app.config['SQLALCHEMY_DATABASE_URI'])
            self.add_engine('default', SqlAlchemyEngine(engine))
        
        binds = app.config.get('SQLALCHEMY_BINDS', {})
        for name, database_uri in binds.items():
            engine = create_engine(database_uri)
            self.add_engine(name, SqlAlchemyEngine(engine))

class SqlAlchemyEngine(Engine):
    def __init__(self, engine):
        self.engine = engine
        self._set_param_style()
        
    def execute(self, query, bind_params):
        with self.engine.connect() as conn:
            result = conn.execute(query, bind_params)
            cols = result.keys()
            rows = result.fetchall()
        table = Table(columns=result.keys(), data=[r.values() for r in rows])
        return table

    def execute_for_json(self, query, bind_params):
        with self.engine.connect() as conn:
            result = conn.execute(finalquery, bindparams)
            return result.fetchone()[0]

    def _set_param_style(self):
        dialect_str = str(type(self.engine.dialect).__module__).lower()
        if 'sqlite' in dialect_str:
            self.param_style = 'qmark'
        elif 'oracle' in dialect_str:
            self.param_style = 'numeric'
        else:
            self.param_style = 'format'            

class SqlView(MethodView):
    def __init__(self, resource_id=None, resource=None):
        if resource:
            self.resource = resource
        elif resource_id:
            squealy = current_app.extensions['squealy']
            self.resource = squealy.get_resource(resource_id)
        else:
            self.resource = None
        
    def build_context(self, request, *args, **kwargs):
        params = request.args.to_dict()
        params.update(kwargs)

        return {
            "params": params
        }

    def get(self, *args, **kwargs):
        squealy = current_app.extensions['squealy']
        if not self.resource:
            self.resource = squealy.get_resource(request.endpoint)
        
        context = self.build_context(request, *args, **kwargs)
        data = self.resource.process(squealy, context)
        return jsonify(data)
