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
    def __init__(self):
        self.qmark_jinja = configure_jinjasql('qmark')
        self.default_jinja = configure_jinjasql('format')
    
    def prepare_query(self, query, context, param_style):
        jinja = self.qmark_jinja if param_style == 'qmark' else self.default_jinja
        final_query, bind_params = jinja.prepare_query(query, context)
        if param_style in ('qmark', 'format', 'numeric'):
            bind_params = list(bind_params)
        return (final_query, bind_params)

def configure_jinjasql(param_style):
    """
    Configure the environment and return jinjaSql object
    """
    utils = """
        {% macro date_range(day, range) -%}
            {{day |safe}} between {{calculate_start_date(range)}} and {{get_today()}}
        {%- endmacro %}
        {% macro date_diff(start_date, end_date, parameter) -%}
            {{ get_date_diff(start_date, end_date, parameter) }}
        {%- endmacro %}
        """
    loader = DictLoader({"utils.sql": utils})
    env = Environment(loader=loader)
    env.globals['get_date_diff'] = get_date_diff
    env.globals['calculate_start_date'] = calculate_start_date
    env.globals['get_today'] = get_today
    return JinjaSql(env, param_style=param_style)


def get_date_diff(start_date, end_date, parameter):
    """
    Returns the difference of month/days/week/years dependending on the parameter
    """
    start_date = datetime.datetime.strptime(start_date, '%Y-%m-%d')
    end_date = datetime.datetime.strptime(end_date, '%Y-%m-%d')

    diff_map = {
        'days': len(list(rrule.rrule(rrule.DAILY, dtstart=start_date, until=end_date))),
        'months': len(list(rrule.rrule(rrule.MONTHLY, dtstart=start_date, until=end_date))),
        'years': len(list(rrule.rrule(rrule.YEARLY, dtstart=start_date, until=end_date))),
        'weeks': len(list(rrule.rrule(rrule.WEEKLY, dtstart=start_date, until=end_date)))
    }
    return diff_map[parameter]


def calculate_start_date(range):
    """
    Jinja filter to return start date based upon the range input and current date
    """
    today = datetime.date.today()

    start_date_mapping = {
        "last_3_days": today + relativedelta(days=-2),
        "last_week": today + relativedelta(days=-6),
        "last_month": today + relativedelta(months=-1),
        "last_quarter": today + relativedelta(months=-2),
        "last_half": today + relativedelta(months=-5),
        "last_year": today + relativedelta(years=-1)
    }

    start_date = start_date_mapping.get(range, None)

    if not start_date:
        raise InvalidDateRangeException("Invalid value for date_range macro in SQL query.")
    return start_date


def get_today():
    return datetime.date.today()
