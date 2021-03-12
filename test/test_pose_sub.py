import json
import zmq
import time
import sys
import pynput

from pynput.mouse import Button, Controller
mouse = Controller()

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

t0 = 0
frame_count = 0

while True:

    # Receives a string format message
    #msg_string = socket.recv_string() 
    #cur_timestamp = time.time()
    #print(msg_string + " (received at " + str(cur_timestamp) + ")")
    t1 = time.time()
    #print("<<< " + json.dumps(msg))
    if(t1 % 1 < t0 % 1):
        print("  FPS: " + str(frame_count) + " (" + format(t0 % 1, '.5f') + " - " + format(t1 % 1, '.5f') + ")")
        frame_count = 0

    t0 = t1
    frame_count += 1

    msg = socket.recv_json() 

    x = msg['objects'][0]['keypoints'][5]['x']
    y = msg['objects'][0]['keypoints'][5]['y']

    #print("[" + str(x) + ", " + str(y) + "]")
    mouse.position = (x, y)
    
