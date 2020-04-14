from requests.exceptions import HTTPError
import requests
import unittest
import os
import jwt

class SquealyTest(unittest.TestCase):
    def setUp(self):
        self.base_url = os.environ.get("BASE_URL", "http://localhost:5000")

        private_key_path = os.environ.get("PRIVATE_KEY", None)
        if not private_key_path:
            tests_dir = os.path.dirname(os.path.realpath(__file__))
            squealy_home_dir = os.path.join(os.path.dirname(tests_dir), "squealy-home")
            private_key_path = os.path.join(squealy_home_dir, "private.pem")

        with open(private_key_path) as f:
            self.private_key = f.read()
    
    def create_jwt_rs256(self, user):
        return jwt.encode(user, self.private_key, algorithm='RS256').decode("utf-8")


    def chart_url(self, chartid):
        return f"{self.base_url}/charts/{chartid}"

    def get_chart(self, chartid, user=None, params=None):
        url = f"{self.base_url}/charts/{chartid}"
        headers = {}
        params = params or {}
        if user:
            jwt = self.create_jwt_rs256(user)
            headers['Authorization'] = f"Bearer {jwt}"

        r = requests.get(url, params=params, headers=headers)
        r.raise_for_status()
        return r.json()


class SecurityTests(SquealyTest):
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

    
    def test_sql_based_authorization(self):
        sri = {"username": "sri"}
        ram = {"username": "ram"}

        self.get_chart("authorization-check-via-sql-query", user=sri, params={"region": 'north'})
        with self.assertRaisesRegex(HTTPError, "403 Client Error"):
            self.get_chart("authorization-check-via-sql-query", user=sri, params={"region": 'east'})

        self.get_chart("authorization-check-via-sql-query", user=ram, params={"region": 'west'})
        with self.assertRaisesRegex(HTTPError, "403 Client Error"):
            self.get_chart("authorization-check-via-sql-query", user=ram, params={"region": 'south'})

        