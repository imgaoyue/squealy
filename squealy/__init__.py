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

# We load the configuration, resources, public key etc. BEFORE we load flask
# This way, if there is a configuration issue, we fail-fast. 
from .loader import load_config, load_objects
from .jinjasql_loader import JinjaWrapper
from squealy import resources as resources_module

config = load_config()
_objects = load_objects(config)
resources = _objects['resources']
_jinja = JinjaWrapper(snippets=_objects['snippets'])

# HACK
# To break a cyclic dependency, we initialize jinja after we have loaded resources and snippets
resources_module.jinja = _jinja

# Next, load flask with the configuration we just loaded
from flask import Flask
from werkzeug.middleware.dispatcher import DispatcherMiddleware
from prometheus_client import make_wsgi_app

# app is used by views.py to register routes
app = Flask(__name__)

# Add prometheus wsgi middleware to route /metrics requests
# application object is then used by wsgi / gunicorn to startup the application
# NOTE: This means prometheus metrics are not exposed in development mode
application = DispatcherMiddleware(app, {
    '/metrics': make_wsgi_app()
})


# Importing views is a circular dependency
# but if we have to use decorators, it is the only way
# Flask documentation has a note on why this is acceptable
# See https://flask.palletsprojects.com/en/1.1.x/patterns/packages/
import squealy.views