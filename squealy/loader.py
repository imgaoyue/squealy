import yaml
from pathlib import Path
from collections import defaultdict
from sqlalchemy import create_engine
from jinja2 import Environment, FileSystemLoader, TemplateNotFound
import os
from .charts import Chart

# This is to ensure parameters.py is loaded
# We load the specific Parameter class dynamically, see get_class
from .parameters import Parameter

def load_config():
    base_dir = os.environ.get("SQUEALY_BASE_DIR", "/squealy/")
    jinja_env = Environment(loader=FileSystemLoader(base_dir))
    config = {"SQUEALY_BASE_DIR": base_dir}
    try:
        template = jinja_env.get_template("config.yml")
    except TemplateNotFound:
        return config

    config_file = template.render({"env": os.environ})
    loaded_config = yaml.safe_load(config_file)
    if loaded_config:
        config.update(loaded_config)
    return config

def load_jwt_public_key(config):
    'Load JWT public key and store it in config.public_key'
    base_dir = config['SQUEALY_BASE_DIR']
    public_key_file = _get_first_file(config.get("PUBLIC_KEY_FILE"), os.path.join(base_dir, "public.pem"))
    if not public_key_file:
        raise Exception("Public key not found. This is needed to verify JWT tokens")
    with open(public_key_file) as f:
        public_key = f.read()
    
    if not public_key.startswith("-----BEGIN PUBLIC KEY-----"):
        raise Exception(f'Public key does not start with -----BEGIN PUBLIC KEY-----')
    config['__PUBLIC_KEY__'] = public_key

def load_charts(config):
    base_dir = config['SQUEALY_BASE_DIR']
    # Yaml files can have jinja templates embedded
    jinja_env = Environment(loader=FileSystemLoader(base_dir))
    engines = _load_datasources(jinja_env, config)

    charts = {}

    # Now load remaining yaml files
    # This time, the config object will also be available
    for ymlfile in Path(base_dir).rglob("*.yml"):
        # skip config.yml since we already processed it before
        if ymlfile.name in ('config.yml', 'datasources.yml'):
            continue
    
        # We load charts in two steps
        # The first pass just loads them as a list of dict objects
        # The second pass creates a Chart object
        # This is because a Chart depends on a data source,
        # and it is possible we load Chart before the data source is loaded
        with open(ymlfile) as f:
            objects = yaml.safe_load_all(f)
            for rawobj in objects:
                kind = rawobj['kind']
                if kind == 'chart':
                    id_ = rawobj.get("id", None)
                    if not id_:
                        raise Exception(f"File {ymlfile} has a Chart without an id field")
                    datasource = rawobj.get("datasource", None)
                    if not datasource:
                        raise Exception(f"Chart {id_} in file {ymlfile} does not have a datasource field")
                    engine = engines.get(datasource, None)
                    if not engine:
                        raise Exception(f"Invalid datasource {datasource} in chart {id_}, file {ymlfile}")
                    chart = _load_chart(rawobj, config, engine)
                    charts[chart.slug] = chart
                elif kind == 'datasource':
                    continue
                else:
                    raise Exception(f"Unknown object of kind = {kind} in {ymlfile}")
    return charts

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

def _load_chart(raw_chart, config, engine):
    id_ = raw_chart['id']
    slug = raw_chart.get('slug', None)
    name = raw_chart.get('name', None)
    query = raw_chart.get('query', None)
    authentication = raw_chart.get('authentication', {"requires_authentication": True})
    raw_params = raw_chart.get('parameters', [])
    param_defns = _parse_parameter_definitions(raw_params)
    requires_authentication = authentication["requires_authentication"]
    
    authorization = raw_chart.get('authorization', [])
    for authz in authorization:
        if 'id' not in authz:
            raise Exception("Authorization rule is missing id")
        if 'query' not in authz:
            raise Exception("Authorization rule is missing query")

    if not query:
        raise Exception(f"Missing query in chart {id_}, file {raw_chart['__sourcefile__']} ")
    
    return Chart(id_, query, engine, slug=slug, name=name, config=config, 
        requires_authentication=requires_authentication,
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
