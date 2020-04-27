import decimal
from werkzeug.exceptions import HTTPException
from .table import Split
from flask.json import JSONEncoder

class InvalidChartDataException(HTTPException):
    code = 404

class Formatter:
    def format(self, table):
        pass

class SimpleFormatter(Formatter):
    def format(self, table):
        data = {"columns": table.columns, "data": [r.values() for r in table.data]}
        return data

class JsonFormatter(Formatter):
    def format(self, table):
        data = [dict(r) for r in table.data]
        return {"data": data}

class GoogleChartsFormatter(Formatter):
    def _generate_chart_data(self, table, column_types):
        """
        Converts the query response to data format desired by google charts
        Google Charts Format ->
        {
            rows: [
                "c":
                    [
                        {
                            "v": series/x-axis label name,
                            "v": value
                        },
                    ], ...
            ],
            cols: [
                {
                    "label": Column name,
                    "type": data type for the column
                }
            ]
        }
        """
        response = {}
        response['rows'] = rows = []
        response['cols'] = cols = []
        
        for index, column in enumerate(table.columns):
            cols.append({"id": column, "label": column, "type": column_types[index]})
        
        for row in table.data:
            row_list = [{"v": e} for e in row]
            rows.append({"c": row_list})
        return response

    def format(self, table):
        # By default, every column is a string
        column_types = ['string'] * len(table.columns)

        # Identify column data types by looking at the first row only
        for row in table.data:
            for index, data in enumerate(row):
                if type(data) in [int, float]:
                    column_types[index] = 'number'
            break
        
        return self._generate_chart_data(table, column_types)