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
import cv2
import trt_pose.coco
import os
import numpy as np
import pickle 

import util_time_profiling

import zmq
import time
import sys

import logging
logging.basicConfig(stream=sys.stderr, level=logging.INFO)

HOST = "0.0.0.0" # Publish to Docker host
PORT = "5001"

ORG_MODEL = 'hand_pose_resnet18_att_244_244.pth'
TRT_MODEL = 'handpose_resnet18_att_224x224_nvhand-2k6_trt.pth'

# Creates a socket instance
context = zmq.Context()
socket = context.socket(zmq.PUB)

# Binds the socket to a predefined port on localhost
socket.bind("tcp://{}:{}".format(HOST, PORT))

DIR = os.path.dirname(os.path.abspath(__file__)) + "/"

with open(DIR + '../json/hand_pose.json', 'r') as f:
    logging.info('reading ../json/hand_pose.json ...')
    hand_pose = json.load(f)

with open(DIR + '../json/msg_pose.json', 'r') as f:
    logging.info('reading ../json/msg_pose.json ...')
    json_pose = json.load(f)

with open(DIR + '../json/obj_hand.json', 'r') as f:
    logging.info('reading ../json/obj_hand.json ...')
    json_hand = json.load(f)

topology = trt_pose.coco.coco_category_to_topology(hand_pose)
logging.debug('import trt_pose.models')
import trt_pose.models

num_parts = len(hand_pose['keypoints'])
num_links = len(hand_pose['skeleton'])

model = trt_pose.models.resnet18_baseline_att(num_parts, 2 * num_links).cuda().eval()
logging.debug('import torchs')
import torch

WIDTH = 224
HEIGHT = 224
data = torch.zeros((1, 3, HEIGHT, WIDTH)).cuda()

if not os.path.exists(DIR + '../model/' + TRT_MODEL):
    logging.info('Did not find: model/' + TRT_MODEL)
    MODEL_WEIGHTS = DIR + '../model/' + ORG_MODEL
    logging.info('Loading     : ../model/' + TRT_MODEL)
    model.load_state_dict(torch.load(MODEL_WEIGHTS))
    logging.debug('import torch2trt')
    import torch2trt
    logging.info('Building    : ../model/' + TRT_MODEL)
    model_trt = torch2trt.torch2trt(model, [data], fp16_mode=True, max_workspace_size=1<<25)
    OPTIMIZED_MODEL = DIR + '../model/' + TRT_MODEL
    torch.save(model_trt.state_dict(), OPTIMIZED_MODEL)

OPTIMIZED_MODEL = DIR + '../model/' + TRT_MODEL
logging.debug('from torch2trt import TRTModule')
from torch2trt import TRTModule

model_trt = TRTModule()
model_trt.load_state_dict(torch.load(OPTIMIZED_MODEL))

logging.debug('print(model_trt)')

from trt_pose.draw_objects import DrawObjects
from trt_pose.parse_objects import ParseObjects

parse_objects = ParseObjects(topology,cmap_threshold=0.15, link_threshold=0.15)
draw_objects = DrawObjects(topology)

logging.debug('import torchvision.transforms as transforms')
logging.debug('import PIL.Image')
import torchvision.transforms as transforms
import PIL.Image

mean = torch.Tensor([0.485, 0.456, 0.406]).cuda()
std = torch.Tensor([0.229, 0.224, 0.225]).cuda()
logging.debug('device = torch.device(\'cuda\')')
device = torch.device('cuda')

from preprocessdata import preprocessdata
preprocessdata = preprocessdata(topology, num_parts)
from gesture_classifier import gesture_classifier
gesture_classifier = gesture_classifier()

filename = DIR + '../model/svmmodel_5class.sav'
clf = pickle.load(open(filename, 'rb'))
with open(DIR + '../json/gesture.json', 'r') as f:
    gesture = json.load(f)
gesture_type = gesture["classes"]

from jetcam.usb_camera import USBCamera
#from jetcam.csi_camera import CSICamera
from jetcam.utils import bgr8_to_jpeg

# TODO: Automatically find YUYV supported camera device ($ v4l2-ctl --device /dev/video* --list-formats)
camera = USBCamera(width=WIDTH, height=HEIGHT, capture_fps=30, capture_device=0)
# TODO: Support CSI camera and pick appropriate camera based on given argument
#camera = CSICamera(width=WIDTH, height=HEIGHT, capture_fps=30)


@util_time_profiling.TimeIt.measure
def get_images():
    try:
        image = camera.read()
    except Exception as e:
        print(str(e))
    return image

@util_time_profiling.TimeIt.measure
def preprocess(image, width, height):
    global device
    mean = torch.Tensor([0.485, 0.456, 0.406]).cuda()
    std = torch.Tensor([0.229, 0.224, 0.225]).cuda()
    device = torch.device('cuda')
    image = cv2.resize(image, (width, height))
    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    image = PIL.Image.fromarray(image)
    image = transforms.functional.to_tensor(image).to(device)
    image.sub_(mean[:, None, None]).div_(std[:, None, None])
    return image[None, ...]

@util_time_profiling.TimeIt.measure
def inference(data):
    cmap, paf = model_trt(data)
    torch.cuda.current_stream().synchronize()
    return cmap, paf

@util_time_profiling.TimeIt.measure
def unwrap_to_tensors(cmap, paf):
    cmap_new, paf_new = cmap.detach().cpu(), paf.detach().cpu()
    return cmap_new, paf_new 

@util_time_profiling.TimeIt.measure
def postprocess(image, cmap, paf):
    logging.debug('5.1. --- in ---')
    logging.debug('5.2. parse_objects()')
    counts, objects, peaks = parse_objects(cmap, paf)
    logging.debug('5.3. joints_inference()')
    joints = preprocessdata.joints_inference(image, counts, objects, peaks)
    logging.debug('5.4. --- return ---')
    return counts, objects, peaks, joints

@util_time_profiling.TimeIt.measure
def create_json(joints, json_pose, json_hand):

    dist_bn_joints = preprocessdata.find_distance(joints)
    gesture = clf.predict([dist_bn_joints,[0]*num_parts*num_parts])
    gesture_joints = gesture[0]
    logging.debug(gesture_type[gesture_joints-1])

    new_pose = json_pose
    new_obj_hand = json_hand
    for i in range(len(joints)):
        new_obj_hand['keypoints'][i]['x'] = joints[i][0]
        new_obj_hand['keypoints'][i]['y'] = joints[i][1]
    new_pose_obj = new_pose['objects']
    new_pose_obj.append(new_obj_hand)
    new_pose['gesture'] = gesture_type[gesture_joints-1]
    return new_pose

@util_time_profiling.TimeIt.measure
def send_json(socket, data):
    q.put(data)

def json_sender(q):
    while True:
        data = q.get()
        socket.send_json(data)
        q.task_done()

@util_time_profiling.TimeIt.measure
def loop_proc():
    # 画像取得
    logging.debug('1. image = get_images()')
    image = get_images()

    # 前処理（変換）
    logging.debug('2. data = preprocess()')
    data = preprocess(image, width=WIDTH, height=HEIGHT)

    # モデルで推論処理
    logging.debug('3. cmap, paf = inference(data)')
    cmap, paf = inference(data)

    # 変換 (GPU -> CPU)
    logging.debug('4. unwrap_to_tensors()')
    #cmap, paf = unwrap_to_tensors(cmap, paf)
    cmap, paf = cmap.detach().cpu(), paf.detach().cpu()    
    
    # 後処理
    logging.debug('5. postprocess()')
    counts, objects, peaks, joints = postprocess(image, cmap, paf)

    # JSON 作成
    logging.debug('6. create_json()')
    msg_pose = create_json(joints, json_pose, json_hand)

    # JSON 送信
    logging.debug('7. send_json()')
    send_json(socket, msg_pose)

from threading import Thread
from queue import Queue
q = Queue()

thread = Thread(target=json_sender, args=(q,))
thread.setDaemon(True)
thread.start()

logging.info('   ###### LOOP ######')
while True:
    loop_proc()
    util_time_profiling.TimeIt.show_result(loop_proc)
