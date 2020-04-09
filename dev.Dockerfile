# This image is meant for local development only

# This base image uses Debian operating system
FROM python:3.7.7-slim

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

# Many python libraries 

COPY requirements.txt .

RUN set -ex \
    && BUILD_DEPS=" \
        build-essential \
        libpcre3-dev \
        libpq-dev \
        python3-dev \
    " \
    && apt-get update && apt-get install -y --no-install-recommends $BUILD_DEPS \
    && pip install --no-cache-dir -r requirements.txt \
    && apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false $BUILD_DEPS \
    && rm -rf /var/lib/apt/lists/*

# Set flask host to 0.0.0.0 so that we can access flask from outside docker
ENV FLASK_RUN_HOST=0.0.0.0

# Set this to the path where oracle native drivers are installed
ENV LD_LIBRARY_PATH /code/drivers/instantclient_19_6

# This is the directory where squealy expects to find config, datasources and charts
ENV SQUEALY_BASE_DIR /code/squealy/fixtures/basic_loading

# The module which contains flask code
ENV FLASK_APP squealy
ENV FLASK_ENV development

# First, find all yml files in SQUEALY_BASE_DIR
# Then, concatenate them into a string with : as separator
# Then, store this string in a variable FILES_TO_WATCH
# Finally, start flask, and instruct it to watch all yml files
CMD /bin/bash -c export FILES_TO_WATCH=$(find /code/squealy/fixtures/basic_loading -type f -name "*.yml" | tr '\n' ':') && echo $FILES_TO_WATCH && flask run 
