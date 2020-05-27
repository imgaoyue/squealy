from jinja2 import DictLoader
from jinja2 import Environment
from jinjasql import JinjaSql
import os
import yaml
from pathlib import Path
from .formatters import JsonFormatter
from itertools import chain

# Try to extend the underyling framework's (django or flask) exception
try:
    from rest_framework.exceptions import APIException as FrameworkHTTPException
except ImportError:
    try:
        from werkzeug.exceptions import HTTPException as FrameworkHTTPException
    except ImportError:
        FrameworkHTTPException = Exception

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
        if not name or not engine:
            raise SquealyConfigException("name or engine is None")
        self.engines[name] = engine
    
    def get_engine(self, name):
        if not name:
            name = 'default'
        return self.engines[name]
    
    def _reload_jinja(self):
        self.jinja = JinjaWrapper(self.snippets)

    def get_jinja(self):
        return self.jinja

    def get_resources(self):
        return dict(self.resources)

    def get_resource(self, _id):
        return self.resources[_id]

    def load_resources(self, base_dir=None, objects=None):
        '''Loads resources, either from yaml files in a directory or from python objects
          
           objects, if provided, must be a list of dictionary objects
        '''
        resources = {}
        snippets = {}

        if base_dir:
            objects_from_dir = self._object_iter(base_dir)
        else:
            objects_from_dir = iter([])
        
        if objects:
            objects_from_memory = iter(objects)
        else:
            objects_from_memory = iter([])

        combined = chain(objects_from_dir, objects_from_memory)
        for rawobj in combined:
            if not rawobj:
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
                    raise SquealyConfigException("Snippet " + _id + " is missing template")
                snippets[_id] = template
            else:
                raise SquealyConfigException("Unknown object of type = " + _type + " in file " + ymlfile)
        
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
        queries = raw_resource.get('queries', None)
        datasource = raw_resource.get('datasource', None)
        formatter = self._load_formatter(raw_resource.get('formatter', 'JsonFormatter'))
        path = raw_resource.get('path', None)

        if not _id:
            raise SquealyConfigException("Resource is missing id " + raw_resource)
        if not queries:
            raise SquealyConfigException("Queries is empty or missing")
        return Resource(_id=_id, queries=queries, datasource=datasource, formatter=formatter, path=path)

    def _load_formatter(self, raw_formatter):
        if not '.' in raw_formatter:
            raw_formatter = "squealy.formatters." + raw_formatter
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
    def __init__(self, _id, queries, datasource=None, formatter=None, path=None, **kwargs):
        if not _id:
            raise SquealyConfigException("Missing id field")
        if not queries:
            raise SquealyConfigException("Queries cannot be empty")

        self.id = _id
        self.queries = Queries(queries)
        self.default_datasource = datasource
        self.formatter = formatter if formatter else JsonFormatter()
        self.path = path

        if len(queries) > 1 and not self.formatter.supports_multi_queries():
            raise SquealyConfigException(type(self.formatter) + " does not support more than 1 query")
        
    def process(self, squealy, initial_context):
        jinja = squealy.get_jinja()
        context = initial_context
        results = None
        for query in self.queries:
            engine = squealy.get_engine(query.datasource or self.default_datasource)
            finalquery, bindparams = jinja.prepare_query(query.query, context, engine.param_style)
            table = engine.execute(finalquery, bindparams)
            
            if query.is_object:
                if len(table) == 0 and not query.is_optional:
                    raise SquealyException("Expected a single row, found none. If 0 rows are expected, you can set isOptional to true")
                if len(table) > 1:
                    raise SquealyException("Expected a single row, found " + len(table) + " rows")
            
            # Lets subsequent queries access data from the current query
            if query.context_key:
                context[query.context_key] = TableProxy(table, 'list' if query.is_list else 'object')
            results = self.formatter.format(results, query, table)
        return results
        
class Queries:
    def __init__(self, queries):
        if not queries:
            raise SquealyConfigException("queries cannot be null / empty")
        if not isinstance(queries, (list, Queries)):
            raise SquealyConfigException("queries must be a list")
        
        if isinstance(queries, list):
            # Single queries are alway root queries
            if len(queries) == 1:
                if not isinstance(queries[0], dict):
                    raise SquealyConfigException('query must be a dict')
                queries[0]['isRoot'] = True
            
            parsed_queries = []
            for query in queries:
                if not isinstance(query, dict):
                    raise SquealyConfigException('query must be a dict')
                parsed_queries.append(Query(**query))
            
            self.queries = parsed_queries
        elif isinstance(queries, Queries):
            self.queries = queries.queries
        self._validate()
        
    def __len__(self):
        return len(self.queries)

    def __iter__(self):
        return iter(self.queries)
    
    @property
    def has_root_query(self):
        if self.root_queries:
            return True
        else:
            return False

    @property
    def shape(self):
        if self.root_queries:
            root = self.root_queries[0]
            if root.is_list:
                return 'list'
            elif root.is_object:
                return 'object'
        else:
            return 'object'

    def _single_root_only(self):
        if len(self.root_queries) > 1:
            raise SquealyConfigException("Multiple root queries found. Either 0 or 1 root query is allowed")
    
    def _validate_shape_list(self):
        if self.shape == 'list':
            for q in self.non_root_queries:
                if q.is_object:
                    raise SquealyConfigException("When the root query is a list, all other queries must also return a list")
                if not q.merge:
                    raise SquealyException("When the root query is a list, merge must be specified in all child queries")
            
    
    @property
    def root_queries(self):
        return [q for q in self.queries if q.is_root]
    
    @property
    def non_root_queries(self):
        return [q for q in self.queries if not q.is_root]

    def _validate(self):
        self._single_root_only()
        self._validate_shape_list()

class Query:
    def __init__(self, contextKey=None, isRoot=False, key=None, queryForList=None, queryForObject=None, datasource=None, merge=None, isOptional=False):
        if queryForList and queryForObject:
            raise SquealyConfigException("Only one of queryForList, queryForObject must be provided, not both")
        if not queryForList and not queryForObject:
            raise SquealyConfigException("At least one of queryForList or queryForObject must be provided")

        self.query = queryForList or queryForObject
        if queryForList:
            self.is_list = True
        elif queryForObject:
            self.is_list = False
        else:
            raise SquealyException("Should not reach here")
        self.is_object = not self.is_list
        
        if not isRoot and not key:
            raise SquealyConfigException("key must be provided for all non-root queries")

        if merge:
            if not ('child' in merge and 'parent' in merge):
                raise SquealyConfigException("merge should specify parent and child columns")
        
        self.context_key = contextKey
        self.is_root = isRoot
        self.key = key
        self.datasource = datasource
        self.is_optional = isOptional
        self.merge = merge
        

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
    
    def __len__(self):
        return len(self.data)

    def as_dict(self):
        result = [dict(zip(self.columns, r)) for r in self.data]
        if self.requires_unflattening:
            result = [Table.unflatten(d) for d in result]
        return result

    # Copied verbatim from https://stackoverflow.com/a/6037657/242940
    @staticmethod
    def unflatten(dictionary):
        resultDict = dict()
        for key, value in dictionary.items():
            parts = key.split(".")
            d = resultDict
            for part in parts[:-1]:
                if part not in d:
                    d[part] = dict()
                d = d[part]
            d[parts[-1]] = value
        return resultDict
    
    @property
    def requires_unflattening(self):
        cols_with_period = [c for c in self.columns if '.' in c]
        if cols_with_period:
            return True
        else:
            return False

class TableProxy:
    def __init__(self, table, shape):
        self._table = table
        if shape in ('list', 'object'):
            self._shape = shape
        else:
            raise SquealyException("Invalid shape - " + shape)
    
    def __getattribute__(self, name):
        table = super().__getattribute__('_table')
        shape = super().__getattribute__('_shape')
        if name in table.columns:
            indx = table.columns.index(name)
            if shape == 'object':
                return table.data[0][indx]
            elif shape == 'list':
                values = [row[indx] for row in table.data]
                return values
            else:
                raise SquealyException("Invalid shape - should not have entered this branch")
        else:
            return super().__getattribute__(name)

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
