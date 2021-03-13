# Copyright (c) 2020-2021, NVIDIA CORPORATION.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json
import zmq
import time
import sys
import pynput

from pynput.mouse import Button, Controller
mouse = Controller()

HOST = "127.0.0.1"
PORT = "5001"

print("--- Subscriber process ---")

# Creates a socket instance
context = zmq.Context()
socket = context.socket(zmq.SUB)

# Connects to a bound socket
socket.connect("tcp://{}:{}".format(HOST, PORT))

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
    mouse.position = (x/224 * 1920, y/224 * 1080)
    
