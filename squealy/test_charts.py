import unittest
from .charts import load_charts
import os
class ChartLoadingTests(unittest.TestCase):
    def test_chart_load(self):
        data = load_charts(fixture_dir("basic_loading"))

def fixture_dir(fixture):
    return os.path.join(os.path.dirname(__file__), "fixtures", fixture)