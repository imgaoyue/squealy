## Getting Started - Django or Django Rest Framework

Install Squealy
    pip install squealy

Create a folder `squealy` parallel to `manage.py`. This is where we will create our resource yaml files.

Create a python module `squealy.py` at the root, with the following contents:

    from squealy.django import DjangoSquealy

    # home_dir should contain one or more yaml files containing the sql queries
    _home_dir = os.path.join(BASE_DIR, "squealy")

    squealy = DjangoSquealy(_home_dir)

Create `sales.yaml` file under `SQUEALY_HOME`, with the following content:

    type: snippet
    name: monthly_sales_data
    template: |
        monthly_sales as (
            SELECT 'jan' as month, 'north' as region, 15 as sales UNION ALL
            SELECT 'jan' as month, 'south' as region, 36 as sales UNION ALL
            SELECT 'feb' as month, 'north' as region, 29 as sales UNION ALL
            SELECT 'feb' as month, 'south' as region, 78 as sales UNION ALL
            SELECT 'mar' as month, 'north' as region, 33 as sales UNION ALL
            SELECT 'mar' as month, 'south' as region, 65 as sales
        )
    ---

    type: resource
    id: monthly_sales
    query: |
        WITH {% include 'monthly_sales_data' %}
        SELECT month, sum(sales) as sales
        FROM monthly_sales 
        GROUP BY month

In `urls.py`, create a route:

    from myproject.squealy import squealy
    import squealy.django.SqlView

    # in urls.py
    urlpatterns = [
        path('monthly-sales/', SqlView.as_view(squealy, 'monthly_sales')),
    ]

If you are using Django Rest Framework, you just need to change your import:

    from myproject.squealy import squealy
    import squealy.django.DrfSqlView as SqlView

    # in urls.py
    urlpatterns = [
        path('monthly-sales/', SqlView.as_view(squealy, 'monthly_sales')),
    ]

`DrfSqlView` extends Django Rest Frameworks' `ApiView` class, so you can configure authentication, authorization etc. classes


## Getting Started - Flask

Install Squealy

    pip install squealy

Create a folder `squealy`. This folder should have the resource yaml files.

In the module where you initialize Flask, do the following : 

    from squealy.flask import FlaskSquealy

    home_dir = '/path/to/squealy'
    squealy = FlaskSquealy(home_dir)

This assumes you are using SqlAlchemy, and have defined the database URI in a property `SQLALCHEMY_DATABASE_URI` or in `SQLALCHEMY_BINDS`.

Next, create `sales.yaml` file under `SQUEALY_HOME`, with the following content:

    type: snippet
    name: monthly_sales_data
    template: |
        monthly_sales as (
            SELECT 'jan' as month, 'north' as region, 15 as sales UNION ALL
            SELECT 'jan' as month, 'south' as region, 36 as sales UNION ALL
            SELECT 'feb' as month, 'north' as region, 29 as sales UNION ALL
            SELECT 'feb' as month, 'south' as region, 78 as sales UNION ALL
            SELECT 'mar' as month, 'north' as region, 33 as sales UNION ALL
            SELECT 'mar' as month, 'south' as region, 65 as sales
        )
    ---

    type: resource
    id: monthly_sales
    query: |
        WITH {% include 'monthly_sales_data' %}
        SELECT month, sum(sales) as sales
        FROM monthly_sales 
        GROUP BY month


To define a view:

    from myapp import app, squealy
    from squealy.flask import SquealyView

    app.add_url_rule('/monthly-sales/', view_func=SquealyView.as_view(squealy, 'monthly_sales'))


---

id: comment_object
type: snippet
template: |
  SELECT c.question_id as '__MERGE_KEY__', c.id as id, c.text as text, c.author_id as 'author.id',
    a.username as 'author.name', a.profile_url as 'author.profileUrl'
  FROM comments c JOIN user a on c.author_id = a.id

---

id: question_object
type: snippet
template: |
  SELECT q.id as '__MERGE_KEY__', q.id as id, q.title as title, q.description as description,
      q.url as url, q.created_at as createdAt, q.author_id as 'author.id', a.username as 'author.name',
      a.profile_url as 'author.profileUrl'
  FROM questions q JOIN user a on q.author_id = a.id

---
    
id: recent-unanswered-questions
queries:
  - id: questions
    isRoot: true
    queryForList: |
      {% include 'question_object' %}
      WHERE q.created_at < {{ params.before | to_timestamp }}
        and NOT EXISTS (
            SELECT 'x' FROM answers a WHERE a.question_id = q.id
        )
      ORDER BY q.created_at desc
      LIMIT 100
  - key: comments
    queryForList: |
      {% include 'comment_object' %}
      WHERE c.question_id in {{ questions['id'] | inclause }}

---

id: question-details
queries: 
  - isRoot: true
    queryForObject: |
      {% include 'question_object' %}
      WHERE q.id = {{params.question_id}}
  - key: comments
    queryForList: |
      {% include 'comment_object' %}
      WHERE c.question_id = {{ params.questiond_id }}
      ORDER BY c.timestamp
  - key: answers
    queryForList: |
      {% include 'answer_object' %}
      WHERE a.question_id = {{ params.question_id }}
      ORDER BY a.votes desc
  
---

id: my-dashboard
queries:
  - key: profile
    queryForObject: |
      SELECT u.id as 'user.id', u.dislay_name as 'user.display_name', u.profile_url as 'user.profileUrl'
      FROM users u
      WHERE u.id = {{ user.id }}
  - key: recentQuestions
    queryForList: |
      SELECT q.id as id, q.title as title, q.body as body
      FROM questions q
      WHERE q.author = {{ user.id }}
      ORDER BY q.timestamp
      LIMIT 10
  - key: recentAnswers
    queryForList: |
      SELECT a.id as id, a.title as title, a.body as body
      FROM answers a 
      WHERE a.author = {{ user.id }}
      ORDER by a.timestamp
      LIMIT 10
