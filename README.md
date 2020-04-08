TODOs:
1. Documentation
1. AuthZ & Validations via SQL Queries
1. Transformations are explicit rather than implicit
1. Parameterize chart type and formatter
1. Separate docker images or flags for developer vs production mode
1. Support hot reloading in developer mode
1. Add support for athena
1. Add support for google spreadsheets
1. Switch to RS256 instead of HS256 based JWT tokens
1. Add support for TLS - gunicorn supports it
1. Expose parameters in charts, these are optional and make the API type safe
1. Generate swagger documentation
1. Add a description column to the chart yaml file
1. Create docker images for MySql, MS SQL and Oracle for testing purposes



Generating Public and Private Key Pair
--------------------------------------

```
openssl genrsa -out private.pem 1024
openssl rsa -in private.pem -outform PEM -pubout -out public.pem
```




