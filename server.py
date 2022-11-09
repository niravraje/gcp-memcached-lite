import socket
import threading
import json
import sys
import firebase_admin
from firebase_admin import db
from google.cloud import storage

# storage_client = storage.Client()
# # The name for the new bucket
# bucket_name = "nirav-bucket"
# bucket = storage.Bucket(storage_client, bucket_name)
# if not bucket.exists():
#     # Creates the new bucket
#     bucket = storage_client.create_bucket(bucket_name)
#     print(f"Bucket {bucket.name} created.")
# blob = bucket.blob("mytest-kv-store.json")
# blob.upload_from_string(data=json.dumps({"nirav": "raje"}), content_type="application/json")
# blob.upload_from_string(data=json.dumps({"abc": "def"}), content_type="application/json")
# contents = blob.download_as_string()
# json_contents = json.loads(contents.decode("utf8"))


IP = "127.0.0.1"
PORT = 7001
ADDR = (IP, PORT)
SIZE = 1024
MESSAGE_FORMAT = "utf-8"
FILE_NAME = "kv-store.json"
FB_SERVICE_ACCOUNT_KEY_PATH = "./secrets/nirav-raje-fall2022-firebase-adminsdk-z38v5-a332390c2e.json"
FB_DATABASE_URL = "https://nirav-raje-fall2022-default-rtdb.firebaseio.com/"


STORAGE_TYPE = "native" # default

print(f"len(sys.argv): {len(sys.argv)}")
if len(sys.argv) > 1:
    arg1_list = sys.argv[1].split("=")
    arg1_key = arg1_list[0]
    arg1_val = arg1_list[-1]
    if arg1_key == "--storage-backend":
        STORAGE_TYPE = arg1_val

print(f"[#] STORAGE_TYPE: {STORAGE_TYPE}")


def cloud_storage_handler(conn, client_addr, blob):
    print(f"[#] Client {client_addr} has connected.")

    while True:
        message = conn.recv(SIZE).decode(MESSAGE_FORMAT)
        if not message:
            break
        print(f"[#] Command received from client {client_addr}:", "\r\n" + message)
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
    conn.close()


def firebase_handler(conn, client_addr, dbref):
    print(f"[#] Client {client_addr} has connected.")

    while True:
        message = conn.recv(SIZE).decode(MESSAGE_FORMAT)
        if not message:
            break
        print(f"[#] Command received from client {client_addr}:", "\r\n" + message)
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
    conn.close()


def native_storage_handler(conn, client_addr):
    print(f"[#] Client {client_addr} has connected.")

    while True:
        message = conn.recv(SIZE).decode(MESSAGE_FORMAT)
        if not message:
            break
        print(f"[#] Command received from client {client_addr}:", "\r\n" + message)
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
    conn.close()

def main():
    print("[#] Server started...")
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(ADDR)
    server.listen()
    print(f"[#] Server listening for connections at address {IP}:{PORT}")

    if STORAGE_TYPE == "firebase":
        print("[#] Initializing Firebase Realtime Database...")
        cred_obj = firebase_admin.credentials.Certificate(FB_SERVICE_ACCOUNT_KEY_PATH)
        firebase_admin.initialize_app(cred_obj, {
            'databaseURL':"https://nirav-raje-fall2022-default-rtdb.firebaseio.com/"
            })
        dbref = db.reference("/")

    elif STORAGE_TYPE == "cloud-storage":
        print("[#] Initializing Cloud Storage...")
        storage_client = storage.Client()
        bucket_name = "memcached-bucket"
        bucket = storage.Bucket(storage_client, bucket_name)
        if not bucket.exists():
            # Creates the new bucket
            bucket = storage_client.create_bucket(bucket_name)
            print(f"Bucket {bucket.name} created.")
        else:
            print(f"Bucket {bucket.name} found.")
        blob = bucket.blob(FILE_NAME)

    while True:
        conn, client_addr = server.accept()
        print(f"[#] Connected to client {client_addr}")

        if STORAGE_TYPE == "firebase":
            thread = threading.Thread(target=firebase_handler, args=(conn, client_addr, dbref))
        elif STORAGE_TYPE == "cloud-storage":
            thread = threading.Thread(target=cloud_storage_handler, args=(conn, client_addr, blob))
        else:
            thread = threading.Thread(target=native_storage_handler, args=(conn, client_addr))
        thread.start()
        print("[#] Number of clients connected: ", threading.active_count() - 1)

if __name__ == "__main__":
    main()