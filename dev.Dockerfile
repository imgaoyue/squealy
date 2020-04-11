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

# These are the libraries needed at run time
# - libpq5 is the postgres native driver, this is needed later when we install psycopg2
# - default-libmysqlclient-dev is needed for MySQL. There may be a lighter package, but we haven't found it out
# - libaio1 is needed for oracle driver
RUN set -ex \
    && apt-get update && apt-get install -y --no-install-recommends libpq5 default-libmysqlclient-dev libaio1 \
    && rm -rf /var/lib/apt/lists/*

# Now install all pip libraries that require compiling native code
# Compiling native code usually requires several build-time packages
# So we install build time package, then install pip libraries, and then uninstall build time packages

COPY requirements.native.txt .

RUN set -ex \
    && BUILD_DEPS=" \
        build-essential \
        libpcre3-dev \
        libpq-dev \
        python3-dev \
    " \
    && apt-get update && apt-get install -y --no-install-recommends $BUILD_DEPS \
    && pip install --no-cache-dir -r requirements.native.txt \
    && apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false $BUILD_DEPS \
    && rm -rf /var/lib/apt/lists/*


COPY requirements.txt .
RUN pip install -r requirements.txt

COPY dev-docker-entrypoint.sh .

ENV FLASK_RUN_HOST "0.0.0.0"
ENV SQUEALY_BASE_DIR "/code/squealy-home"
ENV FLASK_APP "squealy"
ENV FLASK_ENV "development"

# Switch to gunicorn user
# This is to ensure parity with production image
USER gunicorn

ENTRYPOINT [ "/code/dev-docker-entrypoint.sh" ]