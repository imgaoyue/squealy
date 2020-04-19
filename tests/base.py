import requests
import unittest
import os
import jwt

class SquealyTest(unittest.TestCase):
    def setUp(self):
        self.base_url = os.environ.get("BASE_URL", "http://localhost:5000")
        self.base_url_https = os.environ.get("BASE_URL_HTTPS", "https://localhost:8443")

        private_key_path = os.environ.get("PRIVATE_KEY", None)
        if not private_key_path:
            tests_dir = os.path.dirname(os.path.realpath(__file__))
            squealy_home_dir = os.path.join(os.path.dirname(tests_dir), "squealy-home")
            private_key_path = os.path.join(squealy_home_dir, "private.pem")

        with open(private_key_path) as f:
            self.private_key = f.read()
    
    def create_jwt_rs256(self, user):
        return jwt.encode(user, self.private_key, algorithm='RS256').decode("utf-8")


    def chart_url(self, chartid, https=False):
        if https:
            return f"{self.base_url_https}/charts/{chartid}"
        else:
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

