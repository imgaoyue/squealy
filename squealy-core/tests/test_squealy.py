import unittest
from uuid import uuid4
from squealy import Squealy, Resource, Engine, Table
from squealy.formatters import JsonFormatter, SimpleFormatter, SeriesFormatter, GoogleChartsFormatter

class InMemorySqliteEngine(Engine):
    def __init__(self):
        import sqlite3
        self.conn = sqlite3.connect(":memory:")
        self.param_style = 'qmark'

    def execute(self, query, bind_params):
        cursor = self.conn.cursor()
        cursor.execute(query, bind_params)
        cols = [col[0] for col in cursor.description]
        rows = cursor.fetchall()
        return Table(cols, rows)


class ResourceTests(unittest.TestCase):
    def setUp(self):
        snippet = '''
            monthly_sales as (
                SELECT 'jan' as month, 'north' as region, 15 as sales UNION ALL
                SELECT 'jan' as month, 'south' as region, 36 as sales UNION ALL
                SELECT 'feb' as month, 'north' as region, 29 as sales UNION ALL
                SELECT 'feb' as month, 'south' as region, 78 as sales UNION ALL
                SELECT 'mar' as month, 'north' as region, 33 as sales UNION ALL
                SELECT 'mar' as month, 'south' as region, 65 as sales
            )
        '''
        snippets = {'monthly-sales-data': snippet}
        resource = Resource("monthly-sales", """
                            WITH {% include 'monthly-sales-data' %}
                            SELECT month, sum(sales) as sales
                            FROM monthly_sales 
                            {% if params.month %}
                                WHERE month = {{params.month}}
                            {% endif %}
                            GROUP BY month
                            ORDER BY month
                            """)
        resources = {resource.id: resource}
        self.squealy = Squealy(snippets=snippets, resources=resources)
        self.squealy.add_engine(None, InMemorySqliteEngine())

    def test_resource(self):
        resource = self.squealy.get_resource("monthly-sales")
        data = resource.process(self.squealy, {"params": {"month": "jan"}})
        data = data['data']
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0], {'month': 'jan', 'sales': 51})

    def test_simple_formatter(self):
        resource = self._clone_resource("monthly-sales", SimpleFormatter())
        data = resource.process(self.squealy, {"params": {}})
        self.assertEqual(data['columns'], ['month', 'sales'])
        self.assertEqual(data['data'], [('feb', 107), ('jan', 51), ('mar', 98)])
    
    def test_series_formatter(self):
        resource = self._clone_resource("monthly-sales", SeriesFormatter())
        data = resource.process(self.squealy, {"params": {}})
        data = data['data']
        self.assertEqual(data['month'], ['feb', 'jan', 'mar'])
        self.assertEqual(data['sales'], [107, 51, 98])
    
    def test_google_charts_formatter(self):
        resource = self._clone_resource("monthly-sales", GoogleChartsFormatter())
        data = resource.process(self.squealy, {"params": {}})
        self.assertEqual(data['cols'], [
            {'id': 'month', 'label': 'month', 'type': 'string'}, 
            {'id': 'sales', 'label': 'sales', 'type': 'number'}
        ])

        self.assertEqual(data['rows'], [
            {'c': [{'v': 'feb'}, {'v': 107}]}, 
            {'c': [{'v': 'jan'}, {'v': 51}]}, 
            {'c': [{'v': 'mar'}, {'v': 98}]}
        ])

    def test_json_formatter(self):
        resource = self._clone_resource("monthly-sales", JsonFormatter())
        data = resource.process(self.squealy, {"params": {}})
        data = data['data']
        self.assertEqual(len(data), 3)
        self.assertEqual(data[0], {'month': 'feb', 'sales': 107})
        self.assertEqual(data[1], {'month': 'jan', 'sales': 51})
        self.assertEqual(data[2], {'month': 'mar', 'sales': 98})


    def _clone_resource(self, resource_name, formatter):
        resource = self.squealy.get_resource(resource_name)
        cloned = Resource(uuid4(), resource.query, datasource=resource.datasource, formatter=formatter)
        return cloned