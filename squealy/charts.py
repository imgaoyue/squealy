import arrow
import datetime
from werkzeug.exceptions import HTTPException
from pathlib import Path
import yaml
from collections import defaultdict
from sqlalchemy import create_engine
from .jinjasql_loader import configure_jinjasql
from .formatters import GoogleChartsFormatter
from .table import Table

def raw_objects(base_dir):
    for ymlfile in Path(base_dir).rglob("*.yml"):
        with open(ymlfile) as f:
            objects = yaml.safe_load_all(f)
            for rawobj in objects:
                yield (rawobj, ymlfile)

def load_objects(base_dir):
    objects = defaultdict(dict)
    for rawobj, ymlfile in raw_objects(base_dir):
        kind = rawobj['kind']
        if kind == 'chart':
            chart = load_chart(rawobj)
            objects['charts'][chart.slug] = chart
        elif kind == 'datasource':
            url = rawobj['url']
            engine = create_engine(url)
            objects['datasources'][rawobj['id']] = engine
        else:
            raise Exception(f"Unknown object of kind = {kind} in {ymlfile}")
    return objects

def load_chart(raw_chart):
    id_ = raw_chart['id']
    slug = raw_chart['slug'] if 'slug' in raw_chart else id_
    name = raw_chart['name'] if 'name' in raw_chart else id_
    query = raw_chart['query']
    datasource = raw_chart['datasource']
    return Chart(id_, slug, name, query, datasource)

class Chart:
    def __init__(self, id_, slug, name, query, datasource, 
                    transformations=None, formatter=None, options=None):
        self.id_ = id_
        self.slug = slug
        self.name = name
        self.query = query
        self.datasource = datasource
        self.transformations = transformations or []
        self.formatter = formatter if formatter else GoogleChartsFormatter()
        self.options = options or {}

    def process(self, user, params):
        engine = datasources[self.datasource]
        context = {
            "config": config,
            "user": user,
            "params": params
        }

        finalquery, bindparams = jinja.prepare_query(self.query, context)
        with engine.connect() as conn:
            result = conn.execute(finalquery, list(bindparams))
            rows = []
            for db_row in result:
                row_list = []
                for col in db_row:
                    row_list.append(col)
                rows.append(row_list)
            table = Table(columns=result.keys(), data=rows)
            return self.formatter.format(table, 'ColumnChart')

class ChartNotFoundException(HTTPException):
    code = 404
    
class RequiredParameterMissingException(HTTPException):
    code = 400

class DateParseException(HTTPException):
    code = 400

class DateTimeParseException(HTTPException):
    code = 400

class NumberParseException(HTTPException):
    code = 400

class Parameter():
    def __init__(self):
        pass

    def to_internal(self, value):
        return value

class String(Parameter):
    def __init__(self, name, description=None, default_value=None, valid_values=None, **kwargs):
        self.default_value = default_value
        self.valid_values = valid_values
        self.name = name
        self.description = description if description else ""

    def to_internal(self, value):
        if isinstance(value, str):
            return value
        else:
            return str(value)

    def is_valid(self, value):
        if not self.valid_values:
            return True
        if value in self.valid_values:
            return True
        return False


class Date(Parameter):
    def __init__(self, name, description=None, default_value=None, format=None, **kwargs):
        self.default_value = default_value
        self.format = format
        self.name = name
        self.description = description if description else ""
        self.date_macros = {"today": self.today, "tomorrow": self.tomorrow,
                       "next_day": self.tomorrow, "current_day": self.today}

    def today(self, value):
        date = arrow.utcnow()
        return date.date()

    def tomorrow(self, value):
        date = arrow.utcnow()+datetime.timedelta(days=1)
        return date.date()

    def default_formatter(self, value):
        if self.format:
            date = arrow.get(value, self.format)
            return date.date()
        else:
            date = arrow.get(value)
            return date.date()

    def to_internal(self, value):
        try:
            value = value.lower()
            date = self.date_macros.get(value, self.default_formatter)(value)
            return date
        except arrow.parser.ParserError:
            if self.format:
                raise DateParseException("Date could not be parsed: Expected Format- "+self.format+", Received value - "
                                         + value)
            else:
                raise DateParseException("Invalid date: " + value)
        except ValueError as err:
            raise DateParseException(err[0] + ", Received Value - " + value)


class Datetime(Parameter):
    def __init__(self, name, description=None, default_value=None, format=None, **kwargs):
        self.datetime_macros = {"today": self.now, "now": self.now}
        self.default_value = default_value
        self.format = format
        self.name = name
        self.description = description if description else ""

    def now(self, value):
        date = arrow.utcnow()
        return date.datetime

    def default_formatter(self, value):
        if self.format:
            date = arrow.get(value, self.format)
            return date.datetime
        else:
            date = arrow.get(value)
            return date.datetime

    def to_internal(self, value):
        try:
            value = value.lower()
            date_time = self.datetime_macros.get(value, self.default_formatter)(value)
            return date_time
        except arrow.parser.ParserError:
            if self.format:
                raise DateTimeParseException("Datetime could not be parsed: Expected Format - "+self.format
                                             + ", Received value - " + value)
            else:
                raise DateTimeParseException("Invalid DateTime: " + value)
        except ValueError as err:
                raise DateTimeParseException(err[0]+" Recieved Value - " + value)


class Number(Parameter):
    def __init__(self, name, description=None, default_value=None, valid_values=None, **kwargs):
        self.default_value = default_value
        self.valid_values = valid_values
        self.name = name
        self.description = description if description else ""

    def to_internal(self, value):
        try:
            if value.isdigit():
                return int(value)
            else :
                return float(value)
        except ValueError:
            raise NumberParseException("Cannot parse to int or float"+ value)

objects = load_objects("/home/sri/apps/squealy/squealy/fixtures/basic_loading")
charts = objects['charts']
datasources = objects['datasources']
config = objects['config']
jinja = configure_jinjasql()
