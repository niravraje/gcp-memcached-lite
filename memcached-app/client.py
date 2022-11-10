import socket
import time
import sys

IP = "127.0.0.1"
if len(sys.argv) > 1:
    IP = sys.argv[1]
PORT = 7001
ADDR = (IP, PORT)
SIZE = 1024
MESSAGE_FORMAT = "utf-8"

def main():
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect(ADDR)
    print(f"[#] Connection to server established.")

    while True:
        message_p1 = input("> ")
        message_split = message_p1.split()
        command = message_p1.split()[0].lower()
        
        if command == "exit":
            break

        if command == "set":
            key = message_p1.split()[1]
            val_size = message_p1.split()[2]

            message_p2 = input()
            # message formatted as per standard memcached protocol format
            # since this is a simple client, flags and exptime are set to 0
            message = command + " " + key + " 0 0 " + val_size + " \r\n" + message_p2 + "\r\n"
            
        else:
            # standard format of "get" is get <key>, no formatting needed
            message = message_p1 + "\r\n"

        start_time = time.time()
        client.send(message.encode(MESSAGE_FORMAT))
        response = client.recv(SIZE).decode(MESSAGE_FORMAT)
        latency_millis = (time.time() - start_time) * 1000
        

        print(f"[#] Server Response:", "\r\n" + response)
        if command == "get":
            print(f'[#] Standard memcached response format for "get": \nVALUE <key> <flags> <bytes> \r\n<data_block>\r\nEND\r\n')
        print("Response Time (in ms):", latency_millis)


if __name__ == "__main__":
    main()
    