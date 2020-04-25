This software is Work In Progress, do not depend on it just yet.

Thought Process: Why bother about presentation of data? 
Just return the data with as much flexibility as possible

---


TODOs:
1. Rename chart to endpoint
1. Documentation
1. Transformations are explicit rather than implicit
1. Add support for athena and google spreadsheets
1. Generate swagger documentation
1. Add a description column to the chart yaml file
1. Make URLs declarative - don't prepend /charts
1. Support CORS headers via config.yml
1. Export prometheus metrics - Basic is done, now need to expose business metrics
1. Improve logging and error reporting from the point of view of chart developer
    - In development mode, logs are appended to a request scoped object, 
    - which then flushes all log messages in the response somehow?
    - Possible Solution: 
        - Add REQUEST_ID response header in all API calls
        - Provide a dev api which takes REQUEST_ID and provides request scoped logs
        - Store the request logs in memory in a circular buffer-
1. Support pagination in APIs

1. Parameterize chart type and formatter -- PRESENTATION ONLY
1. Separate APIs and Charts. A chart inherits from an API, and adds on additional configuration

DONE
----
1. AuthZ & Validations via SQL Queries - DONE
1. Make JWT tokens optional - i.e. some charts can be public - DONE
1. Switch to uwsgi - because gunicorn is not safe without reverse proxy
1. Integration Tests running via github actions
1. Expose parameters in charts, these are optional and make the API type safe 
1. Add support for TLS - wsgi supports it

Generating Public and Private Key Pair
--------------------------------------

```
openssl genrsa -out private.pem 1024
openssl rsa -in private.pem -outform PEM -pubout -out public.pem
```

Charts Format
-------------
