from flask import request
from werkzeug.exceptions import Unauthorized
from .charts import ChartNotFoundException, Chart
from functools import wraps
import jwt

from squealy import app, charts


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = _extract_token(request)
        if token:
            try:
                request.user = jwt.decode(token, app.config['__PUBLIC_KEY__'], algorithm='RS256')
            except jwt.exceptions.InvalidTokenError as e:
                request.user = None
        else:
            request.user = None
        return f(*args, **kwargs)
    return decorated_function

def _extract_token(request):
    token = request.args.get("accessToken", None)
    if not token:
        auth_header = request.headers.get('Authorization', None)
        if auth_header and 'bearer' in auth_header.lower():
            token = auth_header.split(' ')[1]
    
    return token

@app.route('/charts/<chart_id>')
@login_required
def render_chart(chart_id):
    if not chart_id in charts:
        raise ChartNotFoundException(chart_id)
    chart = charts[chart_id]
    params = request.args
    return chart.process(request.user, params)
