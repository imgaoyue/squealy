from .base import SquealyTest
from requests.exceptions import HTTPError
import requests
import unittest

class SecurityTests(SquealyTest):
    def test_mysql_connection(self):
        chart = self.get_chart("mysql-testing", params={"month": 'jan'})
        self.assertDictEqual(chart, {'columns': ['month', 'sales'], 'data': [['jan', 6543]]})

    def test_postgres_connection(self):
        chart = self.get_chart("postgres-testing", params={"month": 'jan'})
        self.assertDictEqual(chart, {'columns': ['month', 'sales'], 'data': [['jan', 6543]]})

    def test_mssql_connection(self):
        chart = self.get_chart("mssql-testing", params={"month": 'jan'})
        self.assertDictEqual(chart, {'columns': ['month', 'sales'], 'data': [['jan', 6543]]})

    @unittest.skip("Oracle tests can't be run in CI")
    def test_oracle_connection(self):
        chart = self.get_chart("oracle-testing", params={"month": 'jan'})
        self.assertDictEqual(chart, {'columns': ['month', 'sales'], 'data': [['jan', 6543]]})
    