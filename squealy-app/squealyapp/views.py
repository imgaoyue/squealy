from flask import request, current_app
from werkzeug.exceptions import HTTPException, Unauthorized, NotFound
from functools import wraps
import jwt
from squealy import app, resources, config
from .resources import Resource

@app.after_request
def enable_cors(response):
    if config.is_cors_enabled:
        response.headers['Access-Control-Allow-Origin'] = config.cors_allowed_origins
        response.headers['Access-Control-Allow-Methods'] = config.cors_allowed_methods
        response.headers['Access-Control-Allow-Headers'] = config.cors_allowed_headers

    return response

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        request.user = None
        if config.is_authn_enabled:
            token = _extract_token(request)
            if token:
                try:
                    # For now, jwt is the only support authentication mechanism
                    request.user = jwt.decode(token, config.jwt_decode_key, config.jwt_decode_algorithm)
                except jwt.exceptions.InvalidTokenError as e:
                    pass
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

@app.route("/swagger")
def swagger():
    paths = {}
    for resource in resources.values():
        path = {}
        path['summary'] = resource.summary
        path['description'] = resource.description
        path['responses'] = {
            "200": {"description": "A JSON"}
        }
        path['parameters'] = _load_parameters(resource)
        paths[resource.path] = {"get": path}
        

    return {
        "openapi": "3.0.0",
        "info": {
            "title": "Squealy APi",
            "version": "0.1.9"
        },
        "servers": [ 
            {
            "url": request.url_root
            }
        ],
        "paths": paths,
        "components": {
            "securitySchemes": {
            "BearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT"
            }
            }
        },
        "security": [
            {
            "BearerAuth": []
            }
        ]
    }

def _load_parameters(resource):
    parameters = []
    for param in resource.param_defns:
        doc = {"in": "query"}
        doc["name"] = param.name
        doc["description"] = param.description
        doc['required'] = param.mandatory
        doc['description'] = param.description
        
        doc["schema"] = {"type": param.openapi_type()}
        if hasattr(param, 'default_value') and param.default_value:
            doc['schema']['default'] = param.default_value
        if hasattr(param, 'valid_values') and param.valid_values:
            doc['schema']['enum'] = param.valid_values
        
        parameters.append(doc)
    return parameters

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
    app.add_url_rule(path, 'process_resource', process_resource, methods=["GET", "POST", "OPTIONS"], defaults={'resource_id': uuid})