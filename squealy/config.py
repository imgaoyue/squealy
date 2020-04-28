from flask import request, current_app

class SquealyConfig:
    @property
    def is_cors_enabled(self):
        return 'cors' in current_app.config

    @property
    def cors_allowed_origins(self):
        cors_config = current_app.config.get('cors', {})
        origins =  cors_config.get('allowed-origins', [])
        if isinstance(origins, list):
            origins = ",".join(origins)
        return origins
    
    @property
    def cors_allowed_methods(self):
        cors_config = current_app.config.get('cors', {})
        methods = cors_config.get('allowed-methods', ["GET", "OPTIONS"])
        if isinstance(methods, list):
            methods = ",".join(methods)
        return methods
    
    @property
    def cors_allowed_headers(self):
        CORS_ALLOW_HEADERS = [
            'accept',
            'accept-encoding',
            'authorization',
            'content-type',
            'dnt',
            'origin',
            'user-agent',
            'x-csrftoken',
            'x-requested-with',
        ]
        cors_config = current_app.config.get('cors', {})
        headers = cors_config.get('allowed-headers', ", ".join(CORS_ALLOW_HEADERS))
        if isinstance(headers, list):
            headers = ",".join(headers)
        return headers

    @property
    def jwt_decode_key(self):
        return current_app.config['__PUBLIC_KEY__']
    
    @property
    def jwt_decode_algorithm(self):
        return "RS256"
