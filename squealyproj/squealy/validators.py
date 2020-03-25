from jinjasql import JinjaSql
from django.db import connections

from .exceptions import ValidationFailedException

jinjasql = JinjaSql()


def run_validation(params, user, query, db, error_message="Validation Failed"):
    query, bind_params = jinjasql.prepare_query(query, {"params": params, 'user': user})
    conn = connections[db]
    with conn.cursor() as cursor:
        if bind_params:
            cursor.execute(query, bind_params)
        else:
            cursor.execute(query)
        data = cursor.fetchall()
        if len(data) <= 0:
            raise ValidationFailedException(detail=error_message)
