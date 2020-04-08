# We load the configuration, charts, public key etc. BEFORE we load flask
# This way, if there is a configuration issue, we fail-fast. 

# Load the configuration first, and then load charts
from .loader import load_config, load_charts, load_jwt_public_key
_config = load_config()
charts = load_charts(_config)

# This public key is used to verify JWT tokens
load_jwt_public_key(_config)


# Next, load flask with the configuration we just loaded
from flask import Flask
app = Flask(__name__)
app.secret_key = 'secret'
app.config.update(_config)

# app is the canonical name within flask ...
# ... but wsgi / gunicorn expects it to be called application
application = app

# Importing views is a circular dependency
# but if we have to use decorators, it is the only way
# Flask documentation has a note on why this is acceptable
# See https://flask.palletsprojects.com/en/1.1.x/patterns/packages/
import squealy.views