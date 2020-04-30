# Build readonly JSON APIs by writing SQL Queries

Squealy lets you rapidly build readonly REST APIs by writing an SQL query. 

The SQL query can be a jinja template. It supports parameters, macros, filters and other things you expect from a template language. This makes complex, dynamic queries easy to maintain. 

Squealy is safe from sql injection, and it is perfectly safe to embed api parameters directly in the query. Internally, squealy will ensure all parameters are converted to bind parameters, so there is no chance of sql injection.

Developers write an SQL query plus some meta-data in a yaml file. This yaml file is typically version controlled. At run time, Squealy uses these yaml files to serve the APIs.

The generated APIs support authentication via JWT, fine-grained authorization, row level security, parameters and custom validation. 

Squealy is completely stateless and has no runtime dependencies. It runs in a stateless docker container, executes sql queries against the databases you configure, and returns the data as JSON. 


## Why did we build Squealy?

We built Squealy primarily for embedded analytics - i.e. when you want dashboards and charts as part of an existing application. A typical example is a line of business application for employees or vendors. These users would like to see a dashboard with some metrics / kpi as part of the application.

Using a standard BI tool like tableau is very costly, because these tools typically charge per user. Also, the user experience is poor, because the user has to use two different applications.

With Squealy, you would do the following - 
1. Generate a JWT token in your application. Set user specific details such as username, role, department etc. in the JWT token
1. Call Squealy generated APIs to fetch metrics & reports. Pass the JWT token for authentication
1. Use any javascript library to generate the charts. Squealy can return data in a format compatible with many chart libraries such as google charts, chartjs.org, plotly, highcharts etc.


## Quick Start

**Pre-requisites**: You must have docker and docker-compose installed 

1. Create a folder `squealy` and download docker-compose.yml in this folder
1. Run `docker-compose up` and wait a few minutes for the server to start
1. Open `squealy\squealy-home` folder in any text editor. Several example APIs are auto-generated in this folder.
1. Open [http://localhost:3000/swagger](http://localhost:3000/swagger) in a browser

Now you can edit the API definitions in your text editor, and then 

## Key Features

1. Stateless - the chart definitions are in yaml, and typically packaged into the docker image at build time.
1. Not runtime dependencies - Squealy does not require any other database or cache or queue to function
1. Supports complex queries, with templates, conditional logic, macros filters and more.
1. Response can be formatted in different ways to support different charting libraries like chartjs, googlecharts, plotly and so on. 
1. Automatically binds parameters, so this is safe from SQL injection
1. Supports fine-grained security controls - including row level security and authorization rules
1. Supports most relational databases - oracle, sql server, postgres, mysql, redshift, sqlite. Athena and snowflake are in progress. Elasticsearch is also in-progress


## Walkthrough: Building an API for Sales Data

Let's create an API that returns monthly sales aggregate data. The API should take an optional parameter `month` to filter records. Additionally, the API must return records from region(s) that the authenticated user has access to.

This YAML file 

```yaml
kind: resource
path: /reports/monthly-sales
datasource: salesdb
authentication:
    requires_authentication: true
formatter: JsonFormatter
query: |
    SELECT month, sum(sales) as sales from (
        SELECT 'jan' as month, 'north' as region, 10 as sales UNION ALL
        SELECT 'feb' as month, 'north' as region, 20 as sales UNION ALL
        SELECT 'jan' as month, 'south' as region, 30 as sales UNION ALL
        SELECT 'feb' as month, 'south' as region, 40 as sales
    ) s
    WHERE s.region in {{user.regions | inclause }}
    {% if params.month %} and s.month = {{ params.month }} {% endif %}
    GROUP BY month
    ORDER BY month desc
```

Notice the following in the yaml file:

* The `params` object contains all the query parameters passed to the API at runtime.
* The `user` object represents the authenticated user calling the API. Squealy supports JWT tokens for authentication. The user object is created from the JWT token, and hence attributes inside the user object cannot be manipulated.

Based on this, Squealy creates an API at `/reports/monthly-sales`. This API:
* Takes an optional paramter for `month`. 
* Expects either an `Authorization` HTTP header or an `accessToken` query parameter
* JWT token is provided for authentication, and the JWT token has a `region` attribute.

Depending on the user's region that is set in the JWT token:
* Managers will see data from **both** north and south regions
* Regular users will only see data from the region they have access to
* Obviously, you cannot bypass this security by overrding the region 

The response also depends on the `month` parameter:
* If `month` paramater is provided, the data will be restricted to that month only
* If `month` parameter is absent, you will see data from all the months.

The response of the API will be something like this - 

```json
{
  "data": [
    {
      "month": "jan", 
      "sales": 10
    }, 
    {
      "month": "feb", 
      "sales": 20
    }
  ]
}
```


But if you change the formatter to `SeriesFormatter`, the response format will be something more suitable to generating charts using javascript libraries.

```json
{
  "data": {
    "month": ["jan", "feb"], 
    "sales": [10, 20]
  }
}
```

Squealy has several other features, such as - 

* Validation of input parameters
* Fine grained authorization checks that restrict who can call the API and what data they can see
* Performing basic transformations such as pivots and transpose
* Combining data from multiple queries in a single API call
* Support for CORS headers and Cache-Control headers
* Auto-generated Swagger/OpenAPI documentation


## Getting Started

Squealy is distributed as a docker image. There are two docker images.

* `squealy/squalyapi` is meant for production use. It uses a uWSGI based server and has production-ready defaults.
* `squaly/squealy-dev` is meant for local development. It supports live editing based workflows, and provides detailed logs to help during development.


## TODOs:

1. Documentation
1. Add more tests
1. Add support for athena and google spreadsheets
1. Generate swagger documentation
1. Export prometheus metrics - Basic is done, now need to expose business metrics
1. Improve logging and error reporting from the point of view of chart developer
    - In development mode, logs are appended to a request scoped object, 
    - which then flushes all log messages in the response somehow?
    - Possible Solution: 
        - Add REQUEST_ID response header in all API calls
        - Provide a dev api which takes REQUEST_ID and provides request scoped logs
        - Store the request logs in memory in a circular buffer-
1. Support pagination in APIs?


## Generating Public and Private Key Pair

```
openssl genrsa -out private.pem 1024
openssl rsa -in private.pem -outform PEM -pubout -out public.pem
```
