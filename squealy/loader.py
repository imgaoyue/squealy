import yaml
from pathlib import Path
from collections import defaultdict
from sqlalchemy import create_engine
from jinja2 import Environment, FileSystemLoader, TemplateNotFound
import os
from .resources import Resource

# We import Parameter statically for the side-effect
# of loading parameters.py. Parameter is unused, because
# we load the specific Parameter subclass dynamically
from .parameters import Parameter

class ConfigException(Exception):
    pass

def load_config():
    base_dir = _resolve_squealy_base_dir()
    raw_config = _load_config_yaml(base_dir)
    config = SquealyConfig(base_dir, raw_config)
    return config

def _resolve_squealy_base_dir():
    base_dir = os.environ.get("SQUEALY_BASE_DIR", None)
    if not base_dir:
        raise ConfigException("SQUEALY_BASE_DIR environment variable not set")
    
    if not os.path.isdir(base_dir):
        raise ConfigException(f"Path {base_dir} defined in environment variable SQUEALY_BASE_DIR must be a directory")

    return base_dir
    
def _load_config_yaml(base_dir):
    jinja_env = Environment(loader=FileSystemLoader(base_dir))
    try:
        template = jinja_env.get_template("config.yml")
    except TemplateNotFound:
        return {}

    config_file = template.render({"env": os.environ})
    return yaml.safe_load(config_file)
    

def load_objects(config):
    base_dir = config.base_dir
    # Yaml files can have jinja templates embedded
    jinja_env = Environment(loader=FileSystemLoader(base_dir))
    engines = _load_datasources(jinja_env, config)

    resources = {}
    snippets = {}

    # Now load remaining yaml files
    # This time, the config object will also be available
    for ymlfile in Path(base_dir).rglob("*.yml"):
        # skip config.yml since we already processed it before
        if ymlfile.name in ('config.yml', 'datasources.yml'):
            continue
    
        # We load a resource in two steps
        # The first pass just loads them as a list of dict objects
        # The second pass creates a Resource object
        # This is because a Resource depends on a data source,
        # and it is possible we load Resource before the data source is loaded
        with open(ymlfile) as f:
            objects = yaml.safe_load_all(f)
            for rawobj in objects:
                kind = rawobj['kind']
                if kind == 'resource':
                    path = rawobj.get("path", None)
                    if not path:
                        raise ConfigException(f"File {ymlfile} has a Resource without a path")
                    datasource = rawobj.get("datasource", None)
                    if not datasource:
                        raise ConfigException(f"Resource {path} in file {ymlfile} does not have a datasource field")
                    engine = engines.get(datasource, None)
                    if not engine:
                        raise ConfigException(f"Invalid datasource {datasource} in resource {path}, file {ymlfile}")
                    resource = _load_resource(rawobj, config, engine)
                    resources[resource.uuid] = resource
                elif kind == 'snippet':
                    name = rawobj.get("name", None)
                    template = rawobj.get("template", None)
                    if not name:
                        raise ConfigException("Snippet is missing name")
                    if not template:
                        raise ConfigException(f"Snippet {name} is missing template")
                    snippets[name] = template

                else:
                    raise Exception(f"Unknown object of kind = {kind} in {ymlfile}")
    
    return {"resources": resources, "snippets": snippets}

def _load_datasources(jinja_env, config):
    template = jinja_env.get_template("datasources.yml")
    datasources = template.render({"env": os.environ, "config": config})
    datasources = yaml.safe_load(datasources)
    engines = {}
    for raw_source in datasources:
        id_ = raw_source["id"]
        engine = _load_engine(raw_source)
        engines[id_] = engine
    return engines

def _load_engine(rawobj):
    url = rawobj['url']
    engine = create_engine(url)
    _identify_param_style(engine)
    return engine

def _identify_param_style(engine):
    dialect_str = str(type(engine.dialect).__module__).lower()
    if 'sqlite' in dialect_str:
        engine.param_style = 'qmark'
    elif 'oracle' in dialect_str:
        engine.param_style = 'numeric'
    else:
        engine.param_style = 'format'

def _load_resource(raw_resource, config, engine):
    path = raw_resource['path']
    summary = raw_resource.get('summary', None)
    description = raw_resource.get('description', None)
    query = raw_resource.get('query', None)
    authentication = raw_resource.get('authentication', {"requires_authentication": True})
    raw_params = raw_resource.get('parameters', [])
    formatter = _load_formatter(raw_resource.get('formatter', 'SimpleFormatter'))
    param_defns = _parse_parameter_definitions(raw_params)
    requires_authentication = authentication["requires_authentication"]
    
    authorization = raw_resource.get('authorization', [])
    for authz in authorization:
        if 'id' not in authz:
            raise Exception("Authorization rule is missing id")
        if 'query' not in authz:
            raise Exception("Authorization rule is missing query")

    if not query:
        raise Exception(f"Missing query in resource {path}, file {raw_resource['__sourcefile__']} ")
    
    return Resource(path, query, engine, summary=summary, description=description, config=config, 
        requires_authentication=requires_authentication, formatter=formatter,
        authorization=authorization, param_defns=param_defns)


def _parse_parameter_definitions(raw_params):
    params = []
    for raw_param in raw_params:
        kind = raw_param['kind']
        del raw_param['kind']
        if kind in ('String', 'Number', 'Date', 'DateTime'):
            kls = get_class(f'squealy.parameters.{kind}')
            param = kls(**raw_param)
            params.append(param)
    return params

def _load_formatter(raw_formatter):
    if not '.' in raw_formatter:
        raw_formatter = f"squealy.formatters.{raw_formatter}"
    kls = get_class(raw_formatter)
    return kls()

# Copied verbatim from https://stackoverflow.com/questions/452969/does-python-have-an-equivalent-to-java-class-forname
def get_class( kls ):
    parts = kls.split('.')
    module = ".".join(parts[:-1])
    m = __import__( module )
    for comp in parts[1:]:
        m = getattr(m, comp)            
    return m

def _get_first_file(*files):
    for f in files:
        if not f:
            continue
        if os.path.exists(f):
            return f
    return None


class SquealyConfig:
    def __init__(self, base_dir, config):
        self.base_dir = base_dir
        self.config = config
        self._load_authentication()

    @property
    def is_cors_enabled(self):
        return 'cors' in self.config

    @property
    def cors_allowed_origins(self):
        cors_config = self.config.get('cors', {})
        origins =  cors_config.get('allowedOrigins', [])
        if isinstance(origins, list):
            origins = ",".join(origins)
        return origins
    
    @property
    def cors_allowed_methods(self):
        cors_config = self.config.get('cors', {})
        methods = cors_config.get('allowedMethods', ["GET", "OPTIONS"])
        if isinstance(methods, list):
            methods = ",".join(methods)
        return methods
    
    @property
    def cors_allowed_headers(self):
        CORS_ALLOW_HEADERS = [
            'accept',
            'accept-encoding',
            'authorization',
            'content-type',
            'dnt',
            'origin',
            'user-agent',
            'x-csrftoken',
            'x-requested-with',
        ]
        cors_config = self.config.get('cors', {})
        headers = cors_config.get('allowedHeaders', ", ".join(CORS_ALLOW_HEADERS))
        if isinstance(headers, list):
            headers = ",".join(headers)
        return headers

    def _load_authentication(self):
        auth = self.config.get("authentication", None)
        if not auth:
            self._is_authn_enabled = False
            return
        jwt = auth.get("jwt")
        if not jwt:
            self._is_authn_enabled = False
            return
        algo = jwt.get("algorithm", None)
        if not algo or algo not in ('HS256', 'RS256'):
            raise ConfigException("Invalid JWT algorithm. Supported algorithms are HS256 and RS256")

        if algo == 'HS256':
            secret = jwt.get("secret", None)
            if not secret:
                raise ConfigException("secret must be defined when JWT algorithm is HS256")
            self._jwt_decode_key = secret
            self._jwt_decode_algorithm = algo
            self._is_authn_enabled = True
        
        elif algo == 'RS256':
            public_key = jwt.get("publicKey", None)
            public_key_path = jwt.get("publicKeyPath", None)

            if public_key and public_key_path:
                raise ConfigException("When JWT alogithm is RS256, ONLY ONE of publicKey or publicKeyPath must be defined")

            if not public_key and not public_key_path:
                raise ConfigException("When JWT alogithm is RS256, one of publicKey or publicKeyPath must be defined")

            if public_key_path:
                # Relative paths are resolved against the base_dir
                if not os.path.isabs(public_key_path):
                    public_key_path = os.path.join(self.base_dir, public_key_path)
                with open(public_key_path) as f:
                    public_key = f.read()
            if not public_key.startswith("-----BEGIN PUBLIC KEY-----"):
                raise ConfigException('Public key does not start with -----BEGIN PUBLIC KEY-----')
            
            self._jwt_decode_key = public_key
            self._jwt_decode_algorithm = algo
            self._is_authn_enabled = True
        else:
            self._is_authn_enabled = False

    @property
    def is_authn_enabled(self):
        return self._is_authn_enabled
    
    @property
    def jwt_decode_key(self):
        return self._jwt_decode_key
    
    @property
    def jwt_decode_algorithm(self):
        return self._jwt_decode_algorithm
