import os
from flask import Flask
from werkzeug.middleware.dispatcher import DispatcherMiddleware
from prometheus_client import make_wsgi_app
from flask_swagger_ui import get_swaggerui_blueprint
from sqlalchemy.engine import create_engine
from sqlalchemy.exc import SQLAlchemyError
import yaml
from jinja2 import Environment, FileSystemLoader, TemplateNotFound

from squealy import Resource, SquealyConfigException
from squealy.flask import FlaskSquealy, SqlAlchemyEngine, SqlView

def bootstrap():
    config = _load_config()
    app = Flask(__name__)
    app.config.update(config)
    squealy = FlaskSquealy(app, _find_resources_dir(config))
    _load_engines(squealy, config)
    _load_routes(app, squealy)
    _register_swagger(app, config)
    wsgi_app = _add_promethueus_middleware(app)
    return (app, wsgi_app)

def _load_config():
    config_file = os.environ.get('SQUEALY_CONFIG_FILE', None)
    if not config_file:
        raise SquealyConfigException("Environment variable SQUEALY_CONFIG_FILE not set!")

    # Process config file using jinja2, and then parse it as a yaml file
    with open(config_file) as f:
        jinja_env = Environment()
        template = jinja_env.from_string(f.read())
        config_as_string = template.render({"env": os.environ})
        return yaml.safe_load(config_as_string)

def _find_resources_dir(config):
    # If resources_dir is missing, use config dir 
    # If resources_dir is a relative path, assume it is relative to the directory containing config file
    config_dir = os.path.abspath(os.path.dirname(os.environ.get('SQUEALY_CONFIG_FILE')))
    resources_dir = config.get('resources_dir', None)
    if not resources_dir:
        resources_dir = config_dir
    elif not os.path.isabs(resources_dir):
        resources_dir = os.path.join(config_dir, resources_dir)
    if not os.path.exists(resources_dir):
        raise SquealyConfigException(resources_dir + " does not exist!")
    return resources_dir

def _load_engines(squealy, config):
    datasources = config.get('datasources', [])
    if not datasources:
        raise SquealyConfigException("datasources not defined!")
    if not isinstance(datasources, list):
        raise SquealyConfigException("datasources must be a list of objects!")
    
    for datasource in datasources:
        _id = datasource['id']
        url = datasource['url']
        try:
            engine = create_engine(url)
        except SQLAlchemyError as e:
            raise SquealyConfigException("Could not load SQLAlchemy Engine for datasource " + _id + ", url = " + url) from e
        squealy.add_engine(_id, SqlAlchemyEngine(engine))


def _register_swagger(app, config):
    swaggerui_blueprint = get_swaggerui_blueprint(
        '/docs',
        '/swagger',
        config={
            'app_name': "Squealy API Documentation"
        },
    )
    app.register_blueprint(swaggerui_blueprint, url_prefix="/docs")

def _add_promethueus_middleware(app):
    # Add prometheus wsgi middleware to route /metrics requests
    # application object is then used by wsgi / gunicorn to startup the application
    # NOTE: This means prometheus metrics are not exposed in development mode
    wsgi_app = DispatcherMiddleware(app, {
        '/metrics': make_wsgi_app()
    })
    return wsgi_app

def _load_routes(app, squealy):
    # Dynamically register all Resources to the function process_resource
    for _id, resource in squealy.get_resources().items():
        if resource.path:
            app.add_url_rule(resource.path, view_func=SqlView.as_view(_id))


# Expose flask app as module variable
# wsgi_app is used by wsgi.py
app, wsgi_app = bootstrap()

# Importing views is a circular dependency
# but if we have to use decorators, it is the only way
# Flask documentation has a note on why this is acceptable
# See https://flask.palletsprojects.com/en/1.1.x/patterns/packages/

import squealyapp.views

