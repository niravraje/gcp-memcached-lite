#!/bin/bash

# not in use

sudo apt install python3-pip

pip install -r ./memcached-app/requirements.txt

SERVER_INTERNAL_IP=${SERVER_INTERNAL_IP:="127.0.0.1"}
echo "*** SERVER_INTERNAL_IP: ${SERVER_INTERNAL_IP}"
echo "*** STORAGE_BACKEND: ${STORAGE_BACKEND}"

python3 ~/memcached-app/server.py ${SERVER_INTERNAL_IP} --storage-backend=${STORAGE_BACKEND}