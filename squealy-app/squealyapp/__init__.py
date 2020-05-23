from logging.config import dictConfig
import logging 
import os

dictConfig({'version': 1,
    'formatters': {
        'default': {
            'format': '[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
        }
    },
    'handlers': {
        'wsgi': {
            'class': 'logging.StreamHandler',
            'stream': 'ext://flask.logging.wsgi_errors_stream',
            'formatter': 'default'
        }
    },
    'root': {
        'level': 'INFO',
        'handlers': ['wsgi']
    }
})

if os.environ.get('FLASK_ENV', None) == 'development':
    # Instead of memory handler, switch to sqlite handler
    # See https://gist.github.com/giumas/994e48d3c1cff45fbe93

    _memory_handler = logging.handlers.BufferingHandler(2048)
    logging.getLogger('squealy').addHandler(_memory_handler)
    dev_logs = _memory_handler.buffer
else:
    dev_logs = []

# Next, load flask with the configuration we just loaded
from flask import Flask
from werkzeug.middleware.dispatcher import DispatcherMiddleware
from prometheus_client import make_wsgi_app
from flask_swagger_ui import get_swaggerui_blueprint
from sqlalchemy.engine import create_engine
from squealy import Resource
from squealy.flask import FlaskSquealy, SqlAlchemyEngine, SqlView


config = {}

# app is used by views.py to register routes
app = Flask(__name__)
app.config.update(config)

squealy = FlaskSquealy(app, home_dir="/home/sri/apps/squealy/squealy-app/squealy-home")
squealy.add_engine('default', SqlAlchemyEngine(create_engine("sqlite:///:memory:")))

# Register Swagger Blueprint
swaggerui_blueprint = get_swaggerui_blueprint(
    '/docs',
    '/swagger',
    config={
        'app_name': "Squealy API Documentation"
    },
)

app.register_blueprint(swaggerui_blueprint, url_prefix="/docs")

# Add prometheus wsgi middleware to route /metrics requests
# application object is then used by wsgi / gunicorn to startup the application
# NOTE: This means prometheus metrics are not exposed in development mode
application = DispatcherMiddleware(app, {
    '/metrics': make_wsgi_app()
})

def load_routes(app, squealy):
    # Dynamically register all Resources to the function process_resource
    for _id, resource in squealy.get_resources().items():
        if resource.path:
            app.add_url_rule(resource.path, view_func=SqlView.as_view(_id))

load_routes(app, squealy)

# Importing views is a circular dependency
# but if we have to use decorators, it is the only way
# Flask documentation has a note on why this is acceptable
# See https://flask.palletsprojects.com/en/1.1.x/patterns/packages/

# import squealy.views

