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
            params["accessToken"] = jwt
            #headers['Authorization'] = f"Bearer {jwt}"        

        r = requests.get(url, params=params, headers=headers)
        r.raise_for_status()
        return r.json()


class SecurityTests(SquealyTest):
    def test_empty_auth_is_secure(self):
        with self.assertRaisesRegex(HTTPError, "401 Client Error") as e:
            self.get_chart("default-security")
        
        chart = self.get_chart("default-security", user={"username": "sri"})
        self.assertTrue('cols' in chart and 'rows' in chart)
        self.assertEqual(len(chart['rows']), 3)

    def test_anonymous_chart(self):
        chart = self.get_chart("allow-anonymous")
        self.assertTrue('cols' in chart and 'rows' in chart)
        self.assertEqual(len(chart['rows']), 3)

    def test_token_in_header(self):
        url = self.chart_url("default-security")
        token = self.create_jwt_rs256({"username": "sri"})
        r = requests.get(url, headers={"Authorization": f"Bearer {token}"})
        r.raise_for_status()
        
    
