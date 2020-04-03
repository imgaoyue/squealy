from flask import Flask
app = Flask(__name__)
app.secret_key = 'secret'

# Importing views is a circular dependency
# but if we have to use decorators, it is the only way
# Flask documentation has a note on why this is acceptable
# See https://flask.palletsprojects.com/en/1.1.x/patterns/packages/
import squealy.views