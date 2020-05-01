# This base image uses Debian operating system
FROM python:3.7.7-slim

# Create a user gunicorn so that we don't have to use root user
# We switch to gunicorn user at the bottom of this script
RUN groupadd --gid 1000 gunicorn \
  && useradd --uid 1000 --gid gunicorn --shell /bin/bash --create-home gunicorn

# This forces python to not buffer output / error
ENV PYTHONUNBUFFERED 1

# This is where we will copy all our code
# Workdir creates the directory if it doesn't exist
WORKDIR /code

# Now install all pip libraries that require compiling native code
# Compiling native code usually requires several build-time packages
# So we install build time package, then install pip libraries, and then uninstall build time packages

COPY requirements.native.txt .

# RUN_DEPS are needed at run time, BUILD_DEPS are only needed at build time 
# and can be uninstalled immediately after installing pip dependencies
#
# - libpq5 is the postgres native driver, this is needed later when we install psycopg2
# - default-libmysqlclient-dev is needed for MySQL. There may be a lighter package, but we haven't found it out
# - libaio1 is needed for oracle driver
# - build-essential and python3-dev is needed to compile MySQL
# - libssl-dev is needed to enable https support in uwsgi

RUN set -ex \
    && RUN_DEPS=" \
    libpq5 \
    default-libmysqlclient-dev \
    libaio1 \
    " \
    && BUILD_DEPS=" \
        build-essential \
        libpcre3-dev \
        libpq-dev \
        python3-dev \
        libssl-dev \
    " \
    && apt-get update && apt-get install -y --no-install-recommends $BUILD_DEPS $RUN_DEPS \
    && pip install --no-cache-dir -r requirements.native.txt \
    && apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false $BUILD_DEPS \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY docker-entrypoint.sh .

# Copy the remaining code
# Avoid copying the current working directory, 
# as that will have unnecessary files
COPY squealy squealy

# Switch to gunicorn user
# This makes our container a lot more secure
USER gunicorn

# This is the location for oracle's instant client driver
# Users must mount a volume at this path if they wish to connect to Oracle
ENV LD_LIBRARY_PATH /code/drivers/instantclient_19_6/

# Configurations inspired from https://www.caktusgroup.com/blog/2017/03/14/production-ready-dockerfile-your-python-django-app/
ENV UWSGI_WSGI_FILE=squealy/wsgi.py
ENV UWSGI_HTTP=:5000 UWSGI_MASTER=1 UWSGI_HTTP_AUTO_CHUNKED=1 UWSGI_HTTP_KEEPALIVE=1 UWSGI_LAZY_APPS=1 UWSGI_WSGI_ENV_BEHAVIOR=holy
ENV UWSGI_WORKERS=2 UWSGI_THREADS=4

ENTRYPOINT [ "/code/docker-entrypoint.sh" ]
CMD ["uwsgi"]
