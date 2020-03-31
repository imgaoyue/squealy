from werkzeug.exceptions import Unauthorized

from flask import Flask, request
from .charts import charts, ChartNotFoundException, Chart
from functools import wraps
import jwt

app = Flask(__name__)
app.secret_key = "secret"

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.args.get("accessToken", None)
        if not token:
            auth_header = request.headers.get('Authorization', None)
            if not auth_header:
                raise Unauthorized(description="Missing Authorization Token")
            if not 'bearer' in auth_header.lower():
                raise Unauthorized(description="Invalid Authorization Header Format")
            token = auth_header.split(' ')[1]
        try:
            request.user = jwt.decode(token, app.secret_key, algorithm='HS256')
        except jwt.exceptions.InvalidTokenError as e:
            raise Unauthorized(description="Invalid JWT in Authorization Header")
        return f(*args, **kwargs)
    return decorated_function



@app.route('/charts/<chart_id>')
@login_required
def render_chart(chart_id):
    if not chart_id in charts:
        raise ChartNotFoundException(chart_id)
    chart = charts[chart_id]
    params = request.args
    print(request.user)
    return chart.process(request.user, params)