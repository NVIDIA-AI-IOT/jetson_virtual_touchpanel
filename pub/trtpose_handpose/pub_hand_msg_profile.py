import json
import cv2
import matplotlib.pyplot as plt
import matplotlib.image as mpimg 
import trt_pose.coco
import math
import os
import numpy as np

import time_measure_utils

from utils import load_params, load_model, draw_objects, draw_joints, load_image

import zmq
import time
import sys

import logging
logging.basicConfig(stream=sys.stderr, level=logging.INFO)

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
    json_pose = json.load(f)

with open('../json/obj_hand.json', 'r') as f:
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



@time_measure_utils.TimeMeasure.stop_watch
def get_images():
    try:
        image = camera.read()
    except Exception as e:
        print(str(e))
    return image

@time_measure_utils.TimeMeasure.stop_watch
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

@time_measure_utils.TimeMeasure.stop_watch
def inference(data):
    cmap, paf = model_trt(data)
    return cmap, paf

@time_measure_utils.TimeMeasure.stop_watch
def unwrap_to_tensors(cmap, paf):
    cmap_new, paf_new = cmap.detach().cpu(), paf.detach().cpu()
    return cmap_new, paf_new 

@time_measure_utils.TimeMeasure.stop_watch
def postprocess(image, cmap, paf):
    logging.debug('5.1. --- in ---')
    logging.debug('5.2. parse_objects()')
    counts, objects, peaks = parse_objects(cmap, paf)
    logging.debug('5.3. joints_inference()')
    joints = preprocessdata.joints_inference(image, counts, objects, peaks)
    logging.debug('5.4. --- return ---')
    return counts, objects, peaks, joints

@time_measure_utils.TimeMeasure.stop_watch
def create_json(joints, json_pose, json_hand):
    new_pose = json_pose
    new_obj_hand = json_hand
    for i in range(len(joints)):
        new_obj_hand['keypoints'][i]['x'] = joints[i][0]
        new_obj_hand['keypoints'][i]['y'] = joints[i][1]
    new_pose_obj = new_pose['objects']
    new_pose_obj.append(new_obj_hand)
    return new_pose

@time_measure_utils.TimeMeasure.stop_watch
def send_json(socket, data):
    socket.send_json(data)

@time_measure_utils.TimeMeasure.stop_watch
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

logging.info('   ###### LOOP ######')
while True:
    loop_proc()
    time_measure_utils.TimeMeasure.show_time_result(loop_proc)
    time_measure_utils.TimeMeasure.reset_time_result()
