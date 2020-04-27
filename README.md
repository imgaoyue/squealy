This software is Work In Progress, do not depend on it just yet.

---


TODOs:
1. Documentation
1. Add more tests
1. Add support for athena and google spreadsheets
1. Generate swagger documentation
1. Support CORS headers via config.yml
1. Support caching headers in the API
1. Export prometheus metrics - Basic is done, now need to expose business metrics
1. Improve logging and error reporting from the point of view of chart developer
    - In development mode, logs are appended to a request scoped object, 
    - which then flushes all log messages in the response somehow?
    - Possible Solution: 
        - Add REQUEST_ID response header in all API calls
        - Provide a dev api which takes REQUEST_ID and provides request scoped logs
        - Store the request logs in memory in a circular buffer-
1. Support pagination in APIs?

DONE
----
1. Rename chart to Resource
1. Add a description column to the chart yaml file
1. Make URLs declarative - don't prepend /charts
1. AuthZ & Validations via SQL Queries - DONE
1. Make JWT tokens optional - i.e. some charts can be public - DONE
1. Switch to uwsgi - because gunicorn is not safe without reverse proxy
1. Integration Tests running via github actions
1. Expose parameters in charts, these are optional and make the API type safe 
1. Add support for TLS - wsgi supports it
1. Transformations are explicit rather than implicit


Won't Fix
---------
1. Parameterize chart type -- PRESENTATION ONLY
1. Separate APIs and Charts. A chart inherits from an API, and adds on additional configuration

Generating Public and Private Key Pair
--------------------------------------

```
openssl genrsa -out private.pem 1024
openssl rsa -in private.pem -outform PEM -pubout -out public.pem
```

Charts Format
-------------
