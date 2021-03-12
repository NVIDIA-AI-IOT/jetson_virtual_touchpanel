# simple_pub.py
import zmq
import time
import sys

host = "127.0.0.1"
port = "5001"

print("--- Subscriber process ---")

# Creates a socket instance
context = zmq.Context()
socket = context.socket(zmq.SUB)

# Connects to a bound socket
socket.connect("tcp://{}:{}".format(host, port))

# Subscribes to all topics
socket.subscribe("")

while True:

    # Receives a string format message
    msg_string = socket.recv_string() 
    cur_timestamp = time.time()
    print(msg_string + " (received at " + str(cur_timestamp) + ")")
    #msg = socket.recv_json() 
    #print("msg['objects'][0]" + msg['objects'][0])

