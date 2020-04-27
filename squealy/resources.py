import logging
import arrow
import uuid
import datetime
from werkzeug.exceptions import Unauthorized, Forbidden
from .jinjasql_loader import JinjaWrapper
from .formatters import SimpleFormatter
from .table import Table

jinja = JinjaWrapper()
logger= logging.getLogger( __name__ )
class Resource:
    def __init__(self, path, query, engine, name=None, description=None,
            config = None, transformations=None, formatter=None, options=None,
            requires_authentication=True, authorization=None,
            param_defns=None):
        
        # A unique id for this resource
        # This will get regenerated everytime the server starts
        # It is only used internally for routing, and is not exposed to the end user
        self.uuid = uuid.uuid4()

        # Relative url at which this resource will be served
        self.path = path
        
        # The query to execute
        self.query = query
        
        # The database engine against which to execute the query
        self.engine = engine
        self.name = name if name else self.path.replace('/', ' ').strip()
        self.description = description if description else self.name
        
        self.requires_authentication = requires_authentication
        self.authorization = authorization or []
        self.config = config or {}
        self.transformations = transformations or []
        self.formatter = formatter if formatter else SimpleFormatter()
        self.options = options or {}
        self.param_defns = param_defns or []
        
    def process(self, user, params):
        context = {
            "config": self.config,
            "user": user,
            "params": params
        }

        self._authenticate(user)
        self._authorize(context)
        params = self._normalize_parameters(params)

        finalquery, bindparams = jinja.prepare_query(self.query, context, self.engine.param_style)
        with self.engine.connect() as conn:
            result = conn.execute(finalquery, bindparams)
            cols = result.keys()
            rows = result.fetchall()
            
        table = Table(columns=result.keys(), data=rows)
        return self.formatter.format(table)

    def _authenticate(self, user):
        if self.requires_authentication and not user:
            raise Unauthorized()

    def _authorize(self, context):
        if not self.authorization:
            return
        
        for authz in self.authorization:
            finalquery, bindparams = jinja.prepare_query(authz['query'], context, self.engine.param_style)
            with self.engine.connect() as conn:
                result = conn.execute(finalquery, bindparams)
                if not result.first():
                    raise Forbidden(authz['id'])
    
    def _normalize_parameters(self, params):
        for param_defn in self.param_defns:
            name = param_defn.name
            raw_value = params.get(name, None)
            processed_value = param_defn.normalize(raw_value)
            params[name] = processed_value

        return params
