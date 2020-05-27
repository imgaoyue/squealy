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


class LoaderTests(unittest.TestCase):
    def test_load_from_memory(self):
        squealy = Squealy()
        objects = [
            {
                "id": "in-memory-resource",
                "type": "resource",
                "queries": [{
                    "isRoot": True,
                    "queryForList": "SELECT 1 as id, 'sri' as name UNION ALL SELECT 2 as id, 'anshu' as name"
                }]
            }
        ]
        squealy.load_resources(objects=objects)
        squealy.add_engine('default', InMemorySqliteEngine())
        self.assertEqual(len(squealy.get_resources()), 1)
        resource = squealy.get_resource("in-memory-resource")
        data = resource.process(squealy, {"params": {}})
        self.assertEqual(data, {'data': [{'id': 1, 'name': 'sri'}, {'id': 2, 'name': 'anshu'}]})


class ResourceTests(unittest.TestCase):
    def setUp(self):
        self.squealy = Squealy(resources=[])
        self.squealy.add_engine('default', InMemorySqliteEngine())
    
    def test_unflatten(self):
        queries = [{
            "isRoot": True,
            "queryForObject": """SELECT 1 as 'author.id', 'sri' as 'author.displayName', 'Sripathi Krishnan' as 'author.fullName',
                101 as id, 'Does squealy support hierarchial response?' as title
            """
        }]
        resource = Resource("nested-structure", queries=queries)
        data = resource.process(self.squealy, {"params": {}})
        data = data['data']
        self.assertEqual(data, {'author': 
                                    {'id': 1, 'displayName': 'sri', 'fullName': 'Sripathi Krishnan'}, 
                                'id': 101, 'title': 'Does squealy support hierarchial response?'})

    def test_object_resource(self):
        queries = [{
            "isRoot": True,
            "contextKey": "user",
            "queryForObject": "SELECT 2 as id, 'sri' as displayName"
        }, {
            "key": "favouriteFruits",
            "queryForList": """
                SELECT 1 as id, 'Apple' as fruit 
                UNION ALL 
                SELECT 2 as id, 'Banana' as fruit
                """
        }, {
            "key": "address",
            "queryForObject": """
                SELECT 'Bangalore' as city, 'Karnataka' as state, 'India' as country
                """
        }]
        resource = Resource("user-profile", queries=queries)
        data = resource.process(self.squealy, {"params": {}})
        data = data['data']
        self.assertEqual(data, {
            'id': 2, 'displayName': 'sri', 
            'favouriteFruits': [{'id': 1, 'fruit': 'Apple'}, {'id': 2, 'fruit': 'Banana'}], 
            'address': {'city': 'Bangalore', 'state': 'Karnataka', 'country': 'India'}
            })

    def test_independent_keys(self):
        queries = [{
              "key": "profile",
              "queryForObject": "SELECT 2 as id, 'sri' as displayName"

            }, {
              "key": "recentQuestions",
              "queryForList": """SELECT 101 as id, 'How to install Squealy?' as title
                                UNION ALL
                                SELECT 201 as id, 'Can Squealy be extended?' as title
                            """
            }, {
              "key": "recentAnswers",
              "queryForList": """SELECT 401 as id, 'Run pip install squealy' as title
                                UNION ALL
                                SELECT 405 as id, 'Yes, it''s just a library, not a framework' as title
                            """
            }]
        resource = Resource("user-profile", queries=queries)
        data = resource.process(self.squealy, {"params": {}})
        data = data['data']
        self.assertEqual(data, {'profile': {'id': 2, 'displayName': 'sri'}, 
                'recentQuestions': [
                    {'id': 101, 'title': 'How to install Squealy?'}, 
                    {'id': 201, 'title': 'Can Squealy be extended?'}
                ], 
                'recentAnswers': [
                    {'id': 401, 'title': 'Run pip install squealy'}, 
                    {'id': 405, 'title': "Yes, it's just a library, not a framework"}
                ]
            })
    
    def test_list_resource(self):
        queries = [{
              "contextKey": "questions",
              "isRoot": True,
              "queryForList": """
                    SELECT 100 as id, 'How to install Squealy?' as title
                    UNION ALL
                    SELECT 200 as id, 'Can Squealy be extended?' as title
                """

            }, {
              "key": "comments",
              "queryForList": """
                SELECT rs.id as id, rs.qid as qid, rs.comment as comment FROM (
                    SELECT 101 as id, 100 as qid, 'Which OS?' as comment UNION ALL
                    SELECT 102 as id, 100 as qid, 'Ubuntu 18.04' as comment UNION ALL
                    SELECT 103 as id, 100 as qid, 'Ok, pip install squealy' as comment UNION ALL
                    SELECT 201 as id, 200 as qid, 'Yes, it can be extended' as comment UNION ALL
                    SELECT 301 as id, 300 as qid, 'Unrelated comment, should be filtered' as comment
                ) rs
                WHERE rs.qid in {{ questions.id | inclause }}
                """,
               "merge" :{
                   "parent": "id",
                   "child": "qid"
               }
            }]
        resource = Resource("questions-with-comments", queries=queries)
        data = resource.process(self.squealy, {"params": {}})
        data = data['data']
        self.assertEqual(data, [
            {'id': 100, 'title': 'How to install Squealy?', 
                'comments': [{'id': 101, 'qid': 100, 'comment': 'Which OS?'}, 
                            {'id': 102, 'qid': 100, 'comment': 'Ubuntu 18.04'}, 
                            {'id': 103, 'qid': 100, 'comment': 'Ok, pip install squealy'}
            ]}, 
            {'id': 200, 'title': 'Can Squealy be extended?', 
                'comments': [{'id': 201, 'qid': 200, 'comment': 'Yes, it can be extended'}]
            }
        ])

class FormatterTests(unittest.TestCase):
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
        query = """
                WITH {% include 'monthly-sales-data' %}
                SELECT month, sum(sales) as sales
                FROM monthly_sales 
                {% if params.month %}
                    WHERE month = {{params.month}}
                {% endif %}
                GROUP BY month
                ORDER BY month
                """
        
        resource = Resource("monthly-sales", queries=[{"isRoot": True, "queryForList": query}])
        resources = {resource.id: resource}
        self.squealy = Squealy(snippets=snippets, resources=resources)
        self.squealy.add_engine('default', InMemorySqliteEngine())

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
        cloned = Resource(uuid4(), queries=resource.queries, datasource=resource.default_datasource, formatter=formatter)
        return cloned