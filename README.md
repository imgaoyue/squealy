# Build Readonly JSON APIs from SQL Queries

Squealy lets you build readonly REST APIs from template-based SQL or JSON queries. It supports most relational databases, and some NoSQL databases like ElasticSearch.

The SQL query is written as jinja template. You can embed API parameters and user attributes directly into your query, and use conditional logic & looping constructs. In addtion, you can reuse code snipppets, create custom filters and define macros.

Squealy is free from sql injection. It is safe to embed api parameters directly in the query. The templates are evaluated server side, not client side. Internally, squealy uses [JinjaSQL](https://github.com/hashedin/jinjasql) to bind the parameters.

Developers write the SQL query plus some meta-data in a yaml file. At run time, Squealy uses these yaml files to serve the APIs. Squealy has no other metadata other than these yaml files. If you version control the yaml files, you get a completely reproducible setup.

The generated APIs support authentication via JWT, fine-grained authorization, row level security, API parameters and custom validation. The APIs setup appropriate CORS headers and Cache-Control headers as well.

Squealy is completely stateless and has no runtime dependencies. It runs in a stateless docker container, executes sql queries against the database(s) you configure, and returns the data as JSON. 

Squealy supports the following databases - 
* Oracle
* MySQL
* Postgres
* Microsoft SQL Server
* AWS Redshift
* SQLite
* Snowflake (in-progress)
* AWS Athena (in-progress)
* ElasticSearch (in-progress)

## Quick Start

**Pre-requisites**: You must have docker and docker-compose installed 

TBD

## Key Features

1. Stateless - the chart definitions are in yaml, and typically packaged into the docker image at build time.
1. Not runtime dependencies - Squealy does not require any other database or cache or queue to function
1. Supports complex queries, with templates, conditional logic, macros filters and more.
1. Response can be formatted in different ways to support different charting libraries like chartjs, googlecharts, plotly and so on. 
1. Automatically binds parameters, so this is safe from SQL injection
1. Supports fine-grained security controls - including row level security and authorization rules
1. Supports most relational databases - oracle, sql server, postgres, mysql, redshift, sqlite. Athena and snowflake are in progress. Elasticsearch is also in-progress

## Motivation for Squealy

We built Squealy primarily for embedded analytics - i.e. when you want dashboards and charts as part of an existing application. A typical example is a line of business application for employees or vendors. These users would like to see a dashboard with some metrics / kpi as part of the application.

Using a standard BI tool like tableau is very costly, because these tools typically charge per user. Also, the user experience is poor, because the user has to use two different applications.

With Squealy, you would do the following - 
1. Generate a JWT token in your application. Set user specific details such as username, role, department etc. in the JWT token
1. Call Squealy from the UI to fetch metrics & reports. The JWT token created above is used for authentication, so Squealy knows the logged in user, and therefore can enforce authorization rules.
1. Use any javascript library to generate the charts. Squealy can return data in a format compatible with chart libraries such as google charts, chartjs.org, plotly, highcharts etc.

Using such an approach, the application has complete control on the look and feel of the dashboard, giving a rich user experience.


## FAQs
### 1. How does this compare with something like Postgrest?
[Postgrest](http://postgrest.org/en/v7.0.0/)/[pREST](https://postgres.rest/) automatically create CRUD APIs for tables & views. At the moment, Postgrest/pREST only works with Postgres. Squealy focusses only on read APIs, primarily meant for analytics, reporting and business intelligence use cases. 

For security, [Postgrest relies on postgres roles](http://postgrest.org/en/v7.0.0/auth.html). To achieve row level security, you need to rely on Postres Row Level Security, which is tricky to setup correctly. In Squealy, you can directly embed user attributes and api parameters into the sql query. This makes it super simple to achieve fine grained security.

In Postgres/pREST, the data is fetched from a single view or table. This is good for CRUD use cases. But when it comes to reporting or analytics, you typically want to do complex joins, window functions and aggregations - and that's when Squealy comes in handly.

Summary: Use Postgrest/pREST if your use case is transactional, or you want CRUD operations. Use Squealy for read-only use cases, specially in analytics, reporting & business intelligence applications.

### 2. Is Squealy safe from SQL Injection?
Yes, it is.

Suppose your template sql query is this 

```sql
SELECT month, sum(revenue) 
FROM sales s
where s.region = {{ user.region }}
{% if params.month %} and s.month = {{ params.month }} {% endif %}
```

If `month` parameter is provided at runtime, Squealy will execute the following query 

```sql
SELECT month, sum(revenue) 
FROM sales s
where s.region = ?
and s.month = ?
```

If `month` parameter is not provided, the following query will be execute:

```sql
SELECT month, sum(revenue) 
FROM sales s
where s.region = ?
```

In both cases, Squealy will bind the parameters and send them to the database. For more details on how this works, see [JinjaSQL](https://github.com/hashedin/jinjasql).

### Can I use Squealy as a python library instead of a http based service?
It should be possible to use Squealy as a library, though we don't support that use case at the moment. As of now, the recommended approach is to deploy Squealy as a separate container using the provided Docker image. 


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
