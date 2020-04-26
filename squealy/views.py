from flask import request, current_app
from werkzeug.exceptions import HTTPException, Unauthorized, NotFound
from .resources import Resource
from functools import wraps
import jwt

from squealy import app, resources

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = _extract_token(request)
        if token:
            try:
                request.user = jwt.decode(token, current_app.config['__PUBLIC_KEY__'], algorithm='RS256')
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

@login_required
def process_resource(resource_id):
    if not resource_id in resources:
        raise NotFound()
    resource = resources[resource_id]
    params = request.args.to_dict()
    return resource.process(request.user, params)

@app.route('/_logs')
def view_logs():
    from squealy import dev_logs
    from logging import Formatter
    formatter = Formatter()
    logs = [formatter.format(l) for l in dev_logs]
    return {"logs": logs}

# Dynamically register all Resources to the function process_resource
for uuid, resource in resources.items():
    path = resource.path
    uuid = resource.uuid
    app.add_url_rule(path, 'process_resource', process_resource, defaults={'resource_id': uuid})