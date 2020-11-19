# simple_pub.py
import zmq
import time
import sys

rate = int(sys.argv[1])
print("message rate: " + str(1.0/rate))

host = "127.0.0.1"
port = "5001"

# Creates a socket instance
context = zmq.Context()
socket = context.socket(zmq.PUB)

# Binds the socket to a predefined port on localhost
socket.bind("tcp://{}:{}".format(host, port))

time.sleep(1) # new sleep statement

while(True):
    # Sends a string message
    socket.send_string("hello" )
    time.sleep(1.0/rate)
