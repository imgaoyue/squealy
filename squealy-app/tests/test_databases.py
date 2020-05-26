from .base import SquealyTest
from requests.exceptions import HTTPError
import requests
import unittest

class DatabaseIntegrationTests(SquealyTest):
    EXPECTED_DATA = {'data': [{'month': 'jan', 'sales': 6543}]}
    def test_mysql_connection(self):
        chart = self.get_chart("mysql-testing", params={"month": 'jan'})
        self.assertDictEqual(chart, self.EXPECTED_DATA)

    def test_postgres_connection(self):
        chart = self.get_chart("postgres-testing", params={"month": 'jan'})
        self.assertDictEqual(chart, self.EXPECTED_DATA)

    def test_mssql_connection(self):
        chart = self.get_chart("mssql-testing", params={"month": 'jan'})
        self.assertDictEqual(chart, self.EXPECTED_DATA)

    def test_oracle_connection(self):
        chart = self.get_chart("oracle-testing", params={"month": 'jan'})
        self.assertDictEqual(chart, self.EXPECTED_DATA)
    