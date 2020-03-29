from flask import Flask, request

from .charts import charts, ChartNotFoundException, Chart

app = Flask(__name__)

user = {"username": "sripathi", "organization": "hashedin"}

@app.route('/charts/<chart_id>')
def render_chart(chart_id):
    if not chart_id in charts:
        raise ChartNotFoundException(chart_id)
    chart = charts[chart_id]
    params = request.args
    return chart.process(user, params)