from .base import SquealyTest
from requests.exceptions import HTTPError
import requests
import unittest

class SecurityTests(SquealyTest):
    @unittest.skip
    def test_empty_auth_is_secure(self):
        with self.assertRaisesRegex(HTTPError, "401 Client Error") as e:
            self.get_chart("default-security")
        
        chart = self.get_chart("default-security", user={"username": "sri"})
        self.assertDictEqual(chart, {'columns': ['month', 'sales'], 'data': [['jan', 6543], ['feb', 4567], ['mar', 1907]]})

    def test_anonymous_chart(self):
        chart = self.get_chart("allow-anonymous")
        self.assertDictEqual(chart, {'columns': ['month', 'sales'], 'data': [['jan', 6543], ['feb', 4567], ['mar', 1907]]})

    def test_token_in_header(self):
        url = self.chart_url("default-security")
        token = self.create_jwt_rs256({"username": "sri"})
        r = requests.get(url, headers={"Authorization": f"Bearer {token}"})
        r.raise_for_status()

    @unittest.skip    
    def test_row_level_security(self):
        north_user = {"username": "naresh", "regions": ["north"]}
        north_chart = self.get_chart("only-show-data-from-users-region", user=north_user)

        south_user = {"username": "sahil", "regions": ["south"]}
        south_chart = self.get_chart("only-show-data-from-users-region", user=south_user)
        
        super_user = {"username": "admin", "regions": ["north", "south"]}
        super_chart = self.get_chart("only-show-data-from-users-region", user=super_user)

        self.assertEqual(north_chart, {'columns': ['month', 'sales'], 'data': [['jan', 10], ['feb', 20]]})
        self.assertEqual(south_chart, {'columns': ['month', 'sales'], 'data': [['jan', 30], ['feb', 40]]})
        self.assertEqual(super_chart, {'columns': ['month', 'sales'], 'data': [['jan', 40], ['feb', 60]]})

    
    @unittest.skip
    def test_sql_based_authorization(self):
        sri = {"username": "sri"}
        ram = {"username": "ram"}

        # Sri can access north region, but not east
        self.get_chart("authorization-check-via-sql-query", user=sri, params={"region": 'north'})
        with self.assertRaisesRegex(HTTPError, "403 Client Error"):
            self.get_chart("authorization-check-via-sql-query", user=sri, params={"region": 'east'})

        # Ram can access west region, but not south
        self.get_chart("authorization-check-via-sql-query", user=ram, params={"region": 'west'})
        with self.assertRaisesRegex(HTTPError, "403 Client Error"):
            self.get_chart("authorization-check-via-sql-query", user=ram, params={"region": 'south'})

    
    def test_https(self):
        url = self.chart_url("allow-anonymous", https=True)
        r = requests.get(url, verify=False)
        r.raise_for_status()
        
