import json
import zmq
import time
import sys
import math
import random

import logging
logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)

import time_measure_utils

rate = int(sys.argv[1])
print("message rate: " + str(1.0/rate))

host = "127.0.0.1"
port = "5001"

# Creates a socket instance
context = zmq.Context()
socket = context.socket(zmq.PUB)

# Binds the socket to a predefined port on localhost
socket.bind("tcp://{}:{}".format(host, port))

with open('./msg_pose.json', 'r') as f:
    logging.info('reading ./msg_pose.json ...')
    json_pose = json.load(f)

with open('./obj_hand.json', 'r') as f:
    logging.info('reading ./obj_hand.json ...')
    json_hand = json.load(f)

@time_measure_utils.TimeMeasure.stop_watch
def create_json(json_pose, json_hand):
    new_pose = json_pose
    new_obj_hand = json_hand
    for i in range(21):
        new_obj_hand['keypoints'][i]['x'] = random.randint(1,1919)
        new_obj_hand['keypoints'][i]['y'] = random.randint(1,1079)
    
    millisec = time.time() % 1
    new_obj_hand['keypoints'][5]['x'] = int(1920/2 + 500 * math.cos(math.radians(millisec * 360)))
    new_obj_hand['keypoints'][5]['y'] = int(1080/2 + 500 * math.sin(math.radians(millisec * 360)))  
    #new_obj_hand['keypoints'][5]['x'] = int(1920/2)
    #new_obj_hand['keypoints'][5]['y'] = int(1080/2)  
    
    new_pose_obj = new_pose['objects']
    new_pose_obj.clear()
    new_pose_obj.append(new_obj_hand)
    return new_pose

@time_measure_utils.TimeMeasure.stop_watch
def send_json(socket, data):
    socket.send_json(data)

@time_measure_utils.TimeMeasure.stop_watch
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
    time_measure_utils.TimeMeasure.show_time_result(loop_proc)
    time_measure_utils.TimeMeasure.reset_time_result()

