# This Dockerfile builds a production quality, ready to be deployed
# - It copies the src files and ensures Squealy can find them.
# - It sets up HTTPS
# - It copies Oracle drivers


FROM squealy/runtime:latest

# Oracle drivers are not included in the base Squealy image to licensing restrictions
# If you need to connect to Oracle, download oracle instant client to the drivers folder
# and then uncomment the following line
# See drivers/README.md for more information
# 
# COPY drivers /code/drivers

# Uncomment to enable HTTPS Support
# The format is ipaddress:port, /path/to/certificate, /path/to/private-key
# Do not copy the private key and certificate to the Docker image. 
# Instead, mount them using volumes / secrets at runtime
# 
# ENV UWSGI_HTTPS: "0.0.0.0:8443,/code/squealy-home/squealy.crt,/code/squealy-home/squealy.key"


# This is the base directory where Squealy expects to find yaml files
ENV SQUEALY_BASE_DIR /src
COPY src /src
