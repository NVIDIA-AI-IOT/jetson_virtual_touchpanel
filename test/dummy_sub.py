# simple_pub.py
import zmq
import time
import sys

host = "127.0.0.1"
port = "5001"

# Creates a socket instance
context = zmq.Context()
socket = context.socket(zmq.SUB)

# Binds the socket to a predefined port on localhost
socket.bind("tcp://{}:{}".format(host, port))

# Subscribes to all topics
socket.subscribe("")

while True:

    # Receives a string format message
    msg = socket.recv_json() 
    cur_timestamp = time.time()
    print("msg['objects'][0]" + msg['objects'][0])

