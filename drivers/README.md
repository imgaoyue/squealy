Oracle native drivers cannot be distributed or committed to git. If you have to work with Oracle, you need to install it separately.

1. [Download Oracle Instant Client for linux x86-64, Basic Package (ZIP)](https://download.oracle.com/otn_software/linux/instantclient/19600/instantclient-basic-linux.x64-19.6.0.0.0dbru.zip)
1. Unzip it inside ./drivers directory. You should have *.so files in the directory ./drivers/instantclient_19_6/

**Note:**

The instructions assume the folder is called instantclient_19_6. If it changes in future, you would have to update the following places - 
1. LD_LIBRARY_PATH environment variable - this is set in docker-compose.yml file
1. Volume mount for squealy in docker-compose.yml
