from pymemcache.client.base import Client

IP = "127.0.0.1"
PORT = 7001
ADDR = (IP, PORT)
MESSAGE_FORMAT = "utf-8"

client = Client(ADDR)

print("\nNote: The pymemcache client receives the same response as client.py, however the library prints values in its own format.")
print("This client-side script doesn't perform any additional formatting on server response.\n")

# set
print("set response:")
print(client.set("pymemcache_key1", "value1", noreply=False))

# set
print("set response:")
print(client.set("pymemcache_key2", "value2", noreply=False))

# get
print("get response:")
print(client.get("pymemcache_key1").decode(MESSAGE_FORMAT))

# get
print("get response:")
print(client.get("pymemcache_key2").decode(MESSAGE_FORMAT))





