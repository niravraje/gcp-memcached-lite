#!/bin/bash

source ./config.sh

# Set up application default credentials for client libraries
# gcloud auth application-default login

# Create the default network
gcloud compute networks create default || true

# Create firewall rules to allow traffic to instances
gcloud compute firewall-rules create default-rule-allow-internal --network default --allow tcp,udp,icmp --source-ranges 0.0.0.0/0  || true
gcloud compute firewall-rules create default-rule-allow-tcp22-tcp3389-icmp --network default --allow tcp:22,tcp:3389,icmp || true

echo "[#] Server Instance Name: ${SERVER_INSTANCE_NAME}"

# Create server and client instances on GCP
echo "[#] Creating memcached server instance..."
gcloud compute instances create ${SERVER_INSTANCE_NAME} --zone=${INSTANCE_ZONE} --machine-type=${SERVER_MACHINE_TYPE} || true

echo "[#] Creating memcached client instance..."
gcloud compute instances create ${CLIENT_INSTANCE_NAME} --zone=${INSTANCE_ZONE} --machine-type=${CLIENT_MACHINE_TYPE} || true

sleep 2

# Retrieve internal IP of server instance
SERVER_INTERNAL_IP=$(gcloud compute instances describe ${SERVER_INSTANCE_NAME} --zone=${INSTANCE_ZONE} --format='get(networkInterfaces[0].networkIP)')
echo "[#] Server Internal IP: ${SERVER_INTERNAL_IP}"

# SCP the app files into the VM instances
echo "[#] Transferring app files to VM instances..."
gcloud compute scp --recurse memcached-app ${CLIENT_INSTANCE_NAME}:~ --zone=${INSTANCE_ZONE}
gcloud compute scp --recurse memcached-app ${SERVER_INSTANCE_NAME}:~ --zone=${INSTANCE_ZONE}

# Install server dependencies and launch server
# gcloud compute ssh ${SERVER_INSTANCE_NAME} --zone=${INSTANCE_ZONE} -- "SERVER_INTERNAL_IP=${SERVER_INTERNAL_IP} STORAGE_BACKEND=${STORAGE_BACKEND} /bin/bash memcached-app/init-server.sh"
gcloud compute ssh ${SERVER_INSTANCE_NAME} --zone=${INSTANCE_ZONE} -- "sudo apt install python3-pip && pip install -r ./memcached-app/requirements.txt"

gcloud compute ssh ${SERVER_INSTANCE_NAME} --zone=${INSTANCE_ZONE} -- "python3 memcached-app/server.py ${SERVER_INTERNAL_IP} --storage-backend=${STORAGE_BACKEND}"


