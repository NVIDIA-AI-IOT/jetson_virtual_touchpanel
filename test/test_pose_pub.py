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
import os
import sys
import random
import math

import util_time_profiling

import zmq
import time
import sys

import logging
logging.basicConfig(stream=sys.stderr, level=logging.INFO)

rate = int(sys.argv[1])
print("message rate: " + str(1.0/rate))

HOST = "0.0.0.0" # Publish to Docker host
PORT = "5001"

# Creates a socket instance
context = zmq.Context()
socket = context.socket(zmq.PUB)

# Binds the socket to a predefined port on localhost
socket.bind("tcp://{}:{}".format(HOST, PORT))

# Load json files from local directories
DIR = os.path.dirname(os.path.abspath(__file__)) + "/"

with open(DIR + './msg_pose.json', 'r') as f:
    logging.info('reading ./msg_pose.json ...')
    json_pose = json.load(f)

with open(DIR + './obj_hand.json', 'r') as f:
    logging.info('reading ./obj_hand.json ...')
    json_hand = json.load(f)

@util_time_profiling.TimeIt.measure
def create_json(json_pose, json_hand):
    new_pose = json_pose
    new_obj_hand = json_hand
    for i in range(21):
        new_obj_hand['keypoints'][i]['x'] = random.randint(1,1000)
        new_obj_hand['keypoints'][i]['y'] = random.randint(1,1000)
    
    millisec = time.time() % 1
    new_obj_hand['keypoints'][5]['x'] = int(224/2 + 100 * math.cos(math.radians(millisec * 360)))
    new_obj_hand['keypoints'][5]['y'] = int(224/2 + 100 * math.sin(math.radians(millisec * 360)))  

    new_pose_obj = new_pose['objects']
    new_pose_obj.clear()
    new_pose_obj.append(new_obj_hand)
    return new_pose

@util_time_profiling.TimeIt.measure
def send_json(socket, data):
    socket.send_json(data)

@util_time_profiling.TimeIt.measure
def loop_proc():

    # JSON create
    logging.debug('6. create_json()')
    msg_pose = create_json(json_pose, json_hand)

    # JSON submit
    logging.debug('7. send_json()')
    send_json(socket, msg_pose)

    time.sleep(1.0/rate)

logging.info('   ###### LOOP ######')
while True:
    loop_proc()
    util_time_profiling.TimeIt.show_result(loop_proc)

