import json
import cv2
import matplotlib.pyplot as plt
import matplotlib.image as mpimg 
import trt_pose.coco
import math
import os
import numpy as np

from utils import preprocess, load_params, load_model, draw_objects, draw_joints, load_image

import zmq
import time
import sys

import logging
logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)

host = "0.0.0.0" # Publish to Docker host
port = "5001"

# Creates a socket instance
context = zmq.Context()
socket = context.socket(zmq.PUB)

# Binds the socket to a predefined port on localhost
socket.bind("tcp://{}:{}".format(host, port))

with open('../json/hand_pose.json', 'r') as f:
    logging.info('reading ../json/hand_pose.json ...')
    hand_pose = json.load(f)

with open('../json/msg_pose.json', 'r') as f:
    logging.info('reading ../json/msg_pose.json ...')
    msg_pose = json.load(f)

with open('../json/obj_hand.json', 'r') as f:
    logging.info('reading ../json/obj_hand.json ...')
    obj_hand = json.load(f)

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

if not os.path.exists('../model/hand_pose_resnet18_att_244_244_trt.pth'):
    logging.info('Did not find: model/hand_pose_resnet18_att_244_244_trt.pth')
    MODEL_WEIGHTS = '../model/hand_pose_resnet18_att_244_244.pth'
    logging.info('Loading     : ../model/hand_pose_resnet18_att_244_244.pth')
    model.load_state_dict(torch.load(MODEL_WEIGHTS))
    logging.debug('import torch2trt')
    import torch2trt
    logging.info('Building    : ../model/hand_pose_resnet18_att_244_244_trt.pth')
    model_trt = torch2trt.torch2trt(model, [data], fp16_mode=True, max_workspace_size=1<<25)
    OPTIMIZED_MODEL = '../model/hand_pose_resnet18_att_244_244_trt.pth'
    torch.save(model_trt.state_dict(), OPTIMIZED_MODEL)

OPTIMIZED_MODEL = '../model/hand_pose_resnet18_att_244_244_trt.pth'
logging.debug('from torch2trt import TRTModule')
from torch2trt import TRTModule

model_trt = TRTModule()
model_trt.load_state_dict(torch.load(OPTIMIZED_MODEL))

logging.debug('print(model_trt)')
print(model_trt)

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

from jetcam.usb_camera import USBCamera
#from jetcam.csi_camera import CSICamera
from jetcam.utils import bgr8_to_jpeg

camera = USBCamera(width=WIDTH, height=HEIGHT, capture_fps=30, capture_device=0)
#camera = CSICamera(width=WIDTH, height=HEIGHT, capture_fps=30)


#while True:
t0 = time.time()
image = camera.read()
cv2.imwrite('input.jpg', image)

data = preprocess(image, width=WIDTH, height=HEIGHT)
cmap, paf = model_trt(data)
cmap, paf = cmap.detach().cpu(), paf.detach().cpu()
counts, objects, peaks = parse_objects(cmap, paf)
joints = preprocessdata.joints_inference(image, counts, objects, peaks)

new_obj_hand = obj_hand
for i in range(len(joints)):
    new_obj_hand['keypoints'][i]['x'] = joints[i][0]
    new_obj_hand['keypoints'][i]['y'] = joints[i][1]

msg_pose_obj = msg_pose['objects']
msg_pose_obj.append(new_obj_hand)
t1 = time.time()

socket.send_json(msg_pose)

t2 = time.time()
logging.info("  " + format(1.0/(t1-t0), '.2f')+ " fps (" + format(t0 % 1, '.3f') + " - " + format(t1 % 1, '.3f') + " -> " + format(t2 % 1, '.3f') + ")")


# camera.running = True

# def callback(change):
#     t0 = time.time()
#     image = change['new']
#     data = preprocess(image, width=WIDTH, height=HEIGHT)
#     cmap, paf = model_trt(data)
#     cmap, paf = cmap.detach().cpu(), paf.detach().cpu()
#     counts, objects, peaks = parse_objects(cmap, paf)
#     joints = preprocessdata.joints_inference(image, counts, objects, peaks)
    
#     new_obj_hand = obj_hand
#     for i in range(len(joints)):
#         new_obj_hand['keypoints'][i]['x'] = joints[i][0]
#         new_obj_hand['keypoints'][i]['y'] = joints[i][1]

#     msg_pose_obj = msg_pose['objects']
#     msg_pose_obj.append(new_obj_hand)
#     t1 = time.time()

#     socket.send_json(msg_pose)
#     t2 = time.time()
#     logging.info("  " + format(1.0/(t1-t0), '.2f')+ " fps (" + format(t0 % 1, '.3f') + " - " + format(t1 % 1, '.3f') + " -> " + format(t2 % 1, '.3f') + ")")

# logging.debug('camera.observe() called')
# camera.observe(callback, names='value')