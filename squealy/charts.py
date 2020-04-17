import arrow
import datetime
from werkzeug.exceptions import HTTPException, Unauthorized, Forbidden
from .jinjasql_loader import JinjaWrapper
from .formatters import SimpleFormatter
from .table import Table

jinja = JinjaWrapper()

class Chart:
    def __init__(self, id_, query, engine, slug=None, name=None, config = None,
                    transformations=None, formatter=None, options=None,
                    requires_authentication=True, authorization=None):
        # A unique id for this chart
        self.id_ = id_
        
        # The query to execute
        self.query = query
        
        # The database engine against which to execute the query
        self.engine = engine

        self.slug = slug if slug else id_
        self.name = name if name else id_
        
        self.requires_authentication = requires_authentication
        self.authorization = authorization or []
        self.config = config or {}
        self.transformations = transformations or []
        self.formatter = formatter if formatter else SimpleFormatter()
        self.options = options or {}
        
    def process(self, user, params):        
        context = {
            "config": self.config,
            "user": user,
            "params": params
        }

        self._authenticate(user)
        self._authorize(context)
        
        finalquery, bindparams = jinja.prepare_query(self.query, context, self.engine.param_style)
        with self.engine.connect() as conn:
            result = conn.execute(finalquery, bindparams)
            rows = []
            for db_row in result:
                row_list = []
                for col in db_row:
                    row_list.append(col)
                rows.append(row_list)
            table = Table(columns=result.keys(), data=rows)
            return self.formatter.format(table, 'ColumnChart')

    def _authenticate(self, user):
        if self.requires_authentication and not user:
            raise Unauthorized()

    def _authorize(self, context):
        if not self.authorization:
            return
        
        for authz in self.authorization:
            finalquery, bindparams = jinja.prepare_query(authz['query'], context, self.engine.param_style)
            with self.engine.connect() as conn:
                result = conn.execute(finalquery, bindparams)
                if not result.first():
                    raise Forbidden(authz['id'])


class UnauthorizedException(HTTPException):
    code = 401

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
