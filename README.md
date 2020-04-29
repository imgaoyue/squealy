# Build readonly JSON APIs by writing SQL Queries

Squealy lets you rapidly build readonly REST APIs by writing a SQL query. 

Squealy processes SQL queries using [JinjaSQL](https://github.com/hashedin/jinjasql). Placeholders in the query template are automatically converted to bind parameters. Using this approach, you can create complex sql queries using the power of a templating language, and yet not have to worry about sql injection.

Squealy is completely stateless and has no runtime dependencies. It runs in a stateless docker container, run sql queries against the databases you configure and returns the data as JSON objects.

## Motivation
We built Squealy primarily for embedded analytics - i.e. when you want dashboards and charts as part of an existing application. The application generates a JWT token for the logged-in user. The UI authenticates with Squealy with this JWT token, and uses the APIs to generate dashboards and charts.

That said, Squealy is useful whenever you need to build readonly APIs and regular ORM gets in the way.

## Key Features

1. Stateless and easy to deploy - it's just a single docker image with no other dependencies
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
