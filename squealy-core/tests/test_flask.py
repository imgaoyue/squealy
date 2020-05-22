import os
from flask import Flask
from squealy import Resource
from squealy.flask import FlaskSquealy, SqlView, SqlAlchemyEngine
from sqlalchemy import create_engine

app = Flask(__name__)

squealy = FlaskSquealy(app, home_dir=os.path.dirname(__file__))
engine = SqlAlchemyEngine(create_engine("sqlite:///:memory:"))
squealy.add_engine('default', engine)

app.add_url_rule('/squealy/questions', view_func=SqlView.as_view('questions'))

## Test Cases start from here

import unittest
from flask import json

class FlaskTests(unittest.TestCase):
    def test_userprofile(self):
        with app.test_client() as client:
            rv = client.get("/squealy/questions")
            data = json.loads(rv.data)
            self.assertEqual(data['data'], 
                [{'id': 1, 'title': 'How to install squealy?', 
                    'comments': [
                        {'qid': 1, 'comment': 'What OS?'}, 
                        {'qid': 1, 'comment': 'Ubuntu 18.04'}, 
                        {'qid': 1, 'comment': 'Okay - pip install squealy'}
                    ]
                }, {'id': 2, 'title': 'Can Squealy be used in Java?', 
                    'comments': [
                        {'qid': 2, 'comment': 'No, only python for now'}, 
                        {'qid': 2, 'comment': 'You can run in docker and call over http from java'}
                    ]
                }
            ])
