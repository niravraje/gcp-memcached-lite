#!/bin/bash

set -x

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

sleep 5

gcloud compute instances start ${SERVER_INSTANCE_NAME} --zone=${INSTANCE_ZONE}
gcloud compute instances start ${CLIENT_INSTANCE_NAME} --zone=${INSTANCE_ZONE}

sleep 5

# Retrieve internal IP of server instance
SERVER_INTERNAL_IP=$(gcloud compute instances describe ${SERVER_INSTANCE_NAME} --zone=${INSTANCE_ZONE} --format='get(networkInterfaces[0].networkIP)')
echo "[#] Server Internal IP: ${SERVER_INTERNAL_IP}"

# SCP the app files into the VM instances
echo "[#] Transferring app files to VM instances..."
gcloud compute scp --recurse memcached-app ${CLIENT_INSTANCE_NAME}:~ --zone=${INSTANCE_ZONE}
gcloud compute scp --recurse memcached-app ${SERVER_INSTANCE_NAME}:~ --zone=${INSTANCE_ZONE}

# Install server dependencies and launch server
# gcloud compute ssh ${SERVER_INSTANCE_NAME} --zone=${INSTANCE_ZONE} -- "SERVER_INTERNAL_IP=${SERVER_INTERNAL_IP} STORAGE_BACKEND=${STORAGE_BACKEND} /bin/bash memcached-app/init-server.sh"
gcloud compute ssh ${SERVER_INSTANCE_NAME} --zone=${INSTANCE_ZONE} -- "sudo apt-get -qq install python3-pip && pip install -r ./memcached-app/requirements.txt" --quiet

# Start key-value store server process on Server VM (in background)
gcloud compute ssh ${SERVER_INSTANCE_NAME} --zone=${INSTANCE_ZONE} -- "python3 memcached-app/server.py ${SERVER_INTERNAL_IP} --storage-backend=${STORAGE_BACKEND}" &

KVSTORE_SERVER_PID=$!
echo "[#] KVSTORE_SERVER_PID: ${KVSTORE_SERVER_PID}"

sleep 8

# Start key-value store client process on Client VM
gcloud compute ssh ${CLIENT_INSTANCE_NAME} --zone=${INSTANCE_ZONE} -- "python3 memcached-app/client.py ${SERVER_INTERNAL_IP}"

# [Note] Client process will stop only when the user gives the "exit" command

# Fetch server logs from VM
gcloud compute scp --recurse ${SERVER_INSTANCE_NAME}:~/memcached-app/logs/memcached-server.log memcached-app/logs --zone=${INSTANCE_ZONE}

# Kill the kv-store server process that is still running
kill ${KVSTORE_SERVER_PID}

# Stop client & server VMs
gcloud compute instances stop ${SERVER_INSTANCE_NAME} --zone=${INSTANCE_ZONE}
gcloud compute instances stop ${CLIENT_INSTANCE_NAME} --zone=${INSTANCE_ZONE}

# Delete client & server VMs
gcloud compute instances delete ${SERVER_INSTANCE_NAME} --zone=${INSTANCE_ZONE} --delete-disks=all --quiet
gcloud compute instances delete ${CLIENT_INSTANCE_NAME} --zone=${INSTANCE_ZONE} --delete-disks=all --quiet

# Delete all the created firewall-rules
gcloud compute firewall-rules delete default-rule-allow-internal --quiet
gcloud compute firewall-rules delete default-rule-allow-tcp22-tcp3389-icmp --quiet

# Delete the created default network
gcloud compute networks delete default --quiet
