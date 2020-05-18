from jinja2 import DictLoader
from jinja2 import Environment
from jinjasql import JinjaSql
import os
import yaml
from pathlib import Path
from .formatters import JsonFormatter

# Try to extend the underyling framework's (django or flask) exception
try:
    from rest_framework.exceptions import APIException as FrameworkHTTPException
except ImportError:
    try:
        from werkzeug.exceptions import HTTPException as FrameworkHTTPException
    except ImportError:
        FrameworkHTTPException = Exception

# The default engine name if one is not provided
DEFAULT_ENGINE_NAME = '__default_engine__'

class SquealyException(FrameworkHTTPException):
    code = status_code = 500
    description = default_detail = "Internal Server Error"
    default_code = "internal-error"

class BadRequest(FrameworkHTTPException):
    code = status_code = 400
    description = default_detail = "Bad Request"
    default_code = "bad-request"

class SquealyConfigException(SquealyException):
    '''Indicates a configuration problem. 
    
    Should be raised outside of a request/response cycle, typically at startup
    '''
    code = status_code = 500
    description = default_detail = "Bad configuration, check error logs"
    default_code = "bad-configuration"

class Squealy:
    '''
    Container for all resources, data sources and code snippets
    Typically, your application will create an instance at startup and use it throughout
    '''
    def __init__(self, snippets=None, resources=None):
        self.engines = {}
        self.snippets = snippets or {}
        self.resources = resources or {}
        self._reload_jinja()

    def add_engine(self, name, engine):
        'An Engine is responsible for querying an underlying SQL or NoSQL based data source'
        if not name:
            name = DEFAULT_ENGINE_NAME
        self.engines[name] = engine
    
    def get_engine(self, name):
        if not name:
            name = DEFAULT_ENGINE_NAME
        return self.engines[name]
    
    def _reload_jinja(self):
        self.jinja = JinjaWrapper(self.snippets)

    def get_jinja(self):
        return self.jinja

    def get_resource(self, _id):
        return self.resources[_id]

    def load_resources(self, base_dir):
        'Loads resources from yaml files in a directory'
        resources = {}
        snippets = {}

        for raw_obj in self._object_iter(base_dir):
            if not raw_obj:
                continue
            _type = rawobj.get('type', None)
            if not _type:
                continue
            if _type == 'resource':
                resource = self._load_resource(rawobj)
                resources[resource.id] = resource
            elif _type == 'snippet':
                _id = rawobj.get("id", None)
                template = rawobj.get("template", None)
                if not _id:
                    raise SquealyConfigException("Snippet is missing id")
                if not template:
                    raise SquealyConfigException(f"Snippet {_id} is missing template")
                snippets[_id] = template
            else:
                raise SquealyConfigException(f"Unknown object of kind = {kind} in {ymlfile}")
        
        self.resources.update(resources)
        self.snippets.update(snippets)
        self._reload_jinja()

    def _object_iter(self, base_dir):
        for ymlfile in Path(base_dir).rglob("*.yml"):    
            with open(ymlfile) as f:
                objects = yaml.safe_load_all(f)
                for rawobj in objects:
                    yield rawobj

    def _load_resource(self, raw_resource):
        _id = raw_resource.get('id', None)
        query = raw_resource.get('query', None)
        datasource = raw_resource.get('datasource', None)
        formatter = self._load_formatter(raw_resource.get('formatter', 'JsonFormatter'))
        
        if not _id:
            raise SquealyConfigException("Resource is missing id " + raw_resource)
        if not query:
            raise SquealyConfigException(f"Missing query in resource {_id}")
        return Resource(_id, query, datasource, formatter=formatter)

    def _load_formatter(self, raw_formatter):
        if not '.' in raw_formatter:
            raw_formatter = f"squealy.formatters.{raw_formatter}"
        kls = self._get_class(raw_formatter)
        return kls()

    # Copied verbatim from https://stackoverflow.com/questions/452969/does-python-have-an-equivalent-to-java-class-forname
    def _get_class(self, kls):
        parts = kls.split('.')
        module = ".".join(parts[:-1])
        m = __import__( module )
        for comp in parts[1:]:
            m = getattr(m, comp)            
        return m

class Resource:
    def __init__(self, _id, query, datasource=None, formatter=None):
        self.id = _id
        # The query to execute
        self.query = query
        self.datasource = datasource
        self.formatter = formatter if formatter else JsonFormatter()
        
    def process(self, squealy, context):
        engine = squealy.get_engine(self.datasource)
        jinja = squealy.get_jinja()

        finalquery, bindparams = jinja.prepare_query(self.query, context, engine.param_style)
        table = engine.execute(finalquery, bindparams)
        return self.formatter.format(table)

class Engine:
    'A SQL / NoSQL compliant interface to execute a query. Returns a Table'
    def execute(self, query, bind_params):
        pass

    'Similar to execute, but returns a JSON string instead. Useful when the database itself generates JSON'
    def execute_for_json(self, query, bind_params):
        pass

class Table:
    'A basic table that is the result of a sql query'
    def __init__(self, columns=None, data=None):
        self.columns = columns if columns else []
        self.data = data if data else []
    
    def as_dict(self):
        return [dict(zip(self.columns, r)) for r in self.data]

class JinjaWrapper:
    """Wraps JinjaSQL object to work around some quirks in JinjaSQL
    
        Quirk 1: Expose param_style as a function parameter 
        JinjaSQL exposes param_style as a constructor argument. This is less than ideal,
        because we have to support multiple databases and each may have a different param style.
        
        Quirk 2: When param_style = qmark, return a list of bind params
        SQLite requires that bind parameters are provided as a list. But JinjaSQL returns an ordered dict instead.
        So we convert ordered dict to list

    """
    def __init__(self, snippets=None):
        if not snippets:
            snippets = {}
        self.qmark_jinja = self._configure_jinjasql('qmark', snippets)
        self.numeric_jinja = self._configure_jinjasql('numeric', snippets)
        self.default_jinja = self._configure_jinjasql('format', snippets)
    
    def prepare_query(self, query, context, param_style):
        if param_style == 'qmark':
            jinja = self.qmark_jinja
        elif param_style == 'numeric': 
            jinja = self.numeric_jinja
        else:
            jinja = self.default_jinja
        
        final_query, bind_params = jinja.prepare_query(query, context)

        if param_style in ('qmark', 'format', 'numeric'):
            bind_params = list(bind_params)
        elif param_style in ('named', 'pyformat'):
            bind_params = dict(bind_params)
        else:
            raise Exception("Invalid param_style", param_style)
        
        return (final_query, bind_params)

    def _configure_jinjasql(self, param_style, snippets):
        loader = DictLoader(snippets)
        env = Environment(loader=loader)
        return JinjaSql(env, param_style=param_style)
