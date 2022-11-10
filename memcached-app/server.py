import socket
import threading
import json
import sys
import os
import firebase_admin
from firebase_admin import db
from google.cloud import storage
import logging

# default values
IP = "127.0.0.1"
if len(sys.argv) > 1:
    IP = sys.argv[1]
PORT = 7001
ADDR = (IP, PORT)
SIZE = 1024
MESSAGE_FORMAT = "utf-8"
PWD = os.getcwd()
FILE_NAME = "kv-store.json"

FB_SERVICE_ACCOUNT_KEY_PATH = f"{PWD}/memcached-app/secrets/nirav-raje-fall2022-firebase-adminsdk-z38v5-a332390c2e.json"
FB_DATABASE_URL = "https://nirav-raje-fall2022-default-rtdb.firebaseio.com/"

CS_SERVICE_ACCOUNT_KEY_PATH = f"{PWD}/memcached-app/secrets/nirav-raje-fall2022-cloud-storage-84ed9d82b477.json"

STORAGE_TYPE = "native"

print(f"len(sys.argv): {len(sys.argv)}")
logging.info(f"len(sys.argv): {len(sys.argv)}")


if len(sys.argv) > 2:
    arg2_list = sys.argv[2].split("=")
    arg2_key = arg2_list[0]
    arg2_val = arg2_list[-1]
    if arg2_key == "--storage-backend":
        STORAGE_TYPE = arg2_val

print(f"[#] STORAGE_TYPE: {STORAGE_TYPE}")
logging.info(f"[#] STORAGE_TYPE: {STORAGE_TYPE}")


def cloud_storage_handler(conn, client_addr, blob):
    print(f"[#] Client {client_addr} has connected.")
    logging.info(f"[#] Client {client_addr} has connected.")

    while True:
        message = conn.recv(SIZE).decode(MESSAGE_FORMAT)
        if not message:
            break
        print(f"[#] Command received from client {client_addr}:", "\r\n" + message)
        logging.info(f"[#] Command received from client {client_addr}: {message}")
        tokens = message.split()

        if tokens[0].lower() == "set" and len(tokens) >= 5:

            key = tokens[1]
            # tokens[2] and tokens[3] contain the <flags> and <exptime> integers sent by standard memcached clients
            val_size = int(tokens[4])
            val = tokens[-1]
            
            if len(val) != val_size:
                response = "NOT_STORED\r\n"
            else:
                # If blob exists, retrive existing contents in the blob
                if blob.exists():
                    blob_content_bytes = blob.download_as_string()
                    data_dict = json.loads(blob_content_bytes.decode("utf8"))
                else:
                    data_dict = {}
                
                # Add to dict
                data_dict[key] = val

                blob.upload_from_string(data=json.dumps(data_dict), content_type="application/json")

                response = "STORED\r\n"

        elif tokens[0].lower() == "get" and len(tokens) >= 2:
            key = tokens[1]
            try:
                blob_content_bytes = blob.download_as_string()
                data_dict = json.loads(blob_content_bytes.decode("utf8"))
                val = data_dict[key]
                size = len(val)
                response = "VALUE " + str(key) + " 0 " + str(size) + "\r\n" + str(val) + "\r\nEND\r\n"
            except:
                response = "NOT_FOUND\r\n"
        else:
            response = "CLIENT_ERROR Invalid Command\r\n"

        conn.send(response.encode(MESSAGE_FORMAT))
    
    print(f"[#] Connection to {client_addr} closed.")
    logging.info(f"[#] Connection to {client_addr} closed.")
    conn.close()


def firebase_handler(conn, client_addr, dbref):
    print(f"[#] Client {client_addr} has connected.")
    logging.info(f"[#] Client {client_addr} has connected.")

    while True:
        message = conn.recv(SIZE).decode(MESSAGE_FORMAT)
        if not message:
            break
        print(f"[#] Command received from client {client_addr}:", "\r\n" + message)
        logging.info(f"[#] Command received from client {client_addr}: {message}")
        tokens = message.split()

        if tokens[0].lower() == "set" and len(tokens) >= 5:

            key = tokens[1]
            # tokens[2] and tokens[3] contain the <flags> and <exptime> integers sent by standard memcached clients
            val_size = int(tokens[4])
            val = tokens[-1]
            
            if len(val) != val_size:
                response = "NOT_STORED\r\n"
            else:
                dbref.update({key: val})
                response = "STORED\r\n"

        elif tokens[0].lower() == "get" and len(tokens) >= 2:
            key = tokens[1]
            try:
                val = dbref.child(key).get()
                size = len(val)
                response = "VALUE " + str(key) + " 0 " + str(size) + "\r\n" + str(val) + "\r\nEND\r\n"
            except:
                response = "NOT_FOUND\r\n"
        else:
            response = "CLIENT_ERROR Invalid Command\r\n"

        conn.send(response.encode(MESSAGE_FORMAT))
    
    print(f"[#] Connection to {client_addr} closed.")
    logging.info(f"[#] Connection to {client_addr} closed.")
    conn.close()


def native_storage_handler(conn, client_addr):
    print(f"[#] Client {client_addr} has connected.")
    logging.info(f"[#] Client {client_addr} has connected.")

    while True:
        message = conn.recv(SIZE).decode(MESSAGE_FORMAT)
        if not message:
            break
        print(f"[#] Command received from client {client_addr}:", "\r\n" + message)
        logging.info(f"[#] Command received from client {client_addr}: {message}")
        tokens = message.split()

        if tokens[0].lower() == "set" and len(tokens) >= 5:

            key = tokens[1]
            # tokens[2] and tokens[3] contain the <flags> and <exptime> integers sent by standard memcached clients
            val_size = int(tokens[4])
            val = tokens[-1]
            
            if len(val) != val_size:
                response = "NOT_STORED\r\n"
            else:
                # open file for reading and writing, create file if doesn't exist
                with open(FILE_NAME, 'a+') as fp:
                    try:
                        fp.seek(0)
                        data = json.load(fp)
                    except:
                        data = {}

                    try:
                        data[key] = val
                        fp.seek(0)
                        fp.truncate()
                        json.dump(data, fp, indent=4)
                        response = "STORED\r\n"
                    except:
                        response = "NOT_STORED\r\n"

        elif tokens[0].lower() == "get" and len(tokens) >= 2:
            key = tokens[1]
            try:
                with open(FILE_NAME, "r") as fp:
                    data = json.load(fp)
                    val = data[key]
                    size = len(val)
                    # set <flags> to 0 to support compatibility with external clients
                    response = "VALUE " + str(key) + " 0 " + str(size) + "\r\n" + str(val) + "\r\nEND\r\n"
            except:
                response = "NOT_FOUND\r\n"
        else:
            response = "CLIENT_ERROR Invalid Command\r\n"

        conn.send(response.encode(MESSAGE_FORMAT))
    
    print(f"[#] Connection to {client_addr} closed.")
    logging.info(f"[#] Connection to {client_addr} closed.")
    conn.close()

def main():
    # initialize logging configurations
    logging.basicConfig(
        filename=f"{PWD}/memcached-app/logs/memcached-server.log", 
        filemode='w', 
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%d-%b-%y %H:%M:%S',
        level=logging.DEBUG
        )


    print(f"[#] Server started...")
    logging.info(f"[#] Server started...")
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(ADDR)
    server.listen()
    print(f"[#] Server listening for connections at address {IP}:{PORT}")
    logging.info(f"[#] Server listening for connections at address {IP}:{PORT}")

    if STORAGE_TYPE == "firebase":
        print(f"[#] Initializing Firebase Realtime Database...")
        logging.info(f"[#] Initializing Firebase Realtime Database...")
        cred_obj = firebase_admin.credentials.Certificate(FB_SERVICE_ACCOUNT_KEY_PATH)
        firebase_admin.initialize_app(cred_obj, {
            'databaseURL':"https://nirav-raje-fall2022-default-rtdb.firebaseio.com/"
            })
        dbref = db.reference("/")

    elif STORAGE_TYPE == "cloud-storage":
        print("[#] Initializing Cloud Storage...")
        logging.info("[#] Initializing Cloud Storage...")
        # storage_client = storage.Client()
        storage_client = storage.Client.from_service_account_json(json_credentials_path=CS_SERVICE_ACCOUNT_KEY_PATH)
        bucket_name = "memcached-bucket"
        bucket = storage.Bucket(storage_client, bucket_name)
        if not bucket.exists():
            # Creates the new bucket
            bucket = storage_client.create_bucket(bucket_name)
            print(f"Bucket {bucket.name} created.")
            logging.info(f"Bucket {bucket.name} created.")
        else:
            print(f"Bucket {bucket.name} found.")
            logging.info(f"Bucket {bucket.name} found.")
        blob = bucket.blob(FILE_NAME)

    while True:
        conn, client_addr = server.accept()
        print(f"[#] Connected to client {client_addr}")
        logging.info(f"[#] Connected to client {client_addr}")

        if STORAGE_TYPE == "firebase":
            thread = threading.Thread(target=firebase_handler, args=(conn, client_addr, dbref))
        elif STORAGE_TYPE == "cloud-storage":
            thread = threading.Thread(target=cloud_storage_handler, args=(conn, client_addr, blob))
        else:
            thread = threading.Thread(target=native_storage_handler, args=(conn, client_addr))
        thread.start()
        print(f"[#] Number of clients connected: {threading.active_count() - 1}")
        logging.info(f"[#] Number of clients connected: {threading.active_count() - 1}")

if __name__ == "__main__":
    main()