import datetime
from jinja2 import DictLoader
from jinja2 import Environment
from jinjasql import JinjaSql
from dateutil.relativedelta import relativedelta
from dateutil import rrule
from werkzeug.exceptions import HTTPException

class InvalidDateRangeException(HTTPException):
    code = 400

class JinjaWrapper:
    """Wraps JinjaSQL object to work around some quirks in JinjaSQL
    
        Quirk 1: Expose param_style as a function parameter 
        JinjaSQL exposes param_style as a constructor argument. This is less than ideal,
        because we have to support multiple databases and each may have a different param style.
        
        Quirk 2: When param_style = qmark, return a list of bind params
        SQLite requires that bind parameters are provided as a list. But JinjaSQL returns an ordered dict instead.
        So we convert ordered dict to list

    """
    def __init__(self, snippets=None):
        if not snippets:
            snippets = {}
        self.qmark_jinja = configure_jinjasql('qmark', snippets)
        self.numeric_jinja = configure_jinjasql('numeric', snippets)
        self.default_jinja = configure_jinjasql('format', snippets)
    
    def prepare_query(self, query, context, param_style):
        if param_style == 'qmark':
            jinja = self.qmark_jinja
        elif param_style == 'numeric': 
            jinja = self.numeric_jinja
        else:
            jinja = self.default_jinja
        
        final_query, bind_params = jinja.prepare_query(query, context)

        if param_style in ('qmark', 'format', 'numeric'):
            bind_params = list(bind_params)
        elif param_style in ('named', 'pyformat'):
            bind_params = dict(bind_params)
        else:
            raise Exception("Invalid param_style", param_style)
        
        return (final_query, bind_params)

def configure_jinjasql(param_style, snippets):
    loader = DictLoader(snippets)
    env = Environment(loader=loader)
    return JinjaSql(env, param_style=param_style)
