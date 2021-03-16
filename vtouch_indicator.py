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

import os
import gi
import subprocess
import time
import threading
import re
import sys
import multiprocessing as mp
import zmq
import vtouch as vt

zmq_host = "127.0.0.1"
zmq_port = "5001"

gi.require_version("Gtk", "3.0")
gi.require_version('AppIndicator3', '0.1')
gi.require_version('Notify', '0.7')

from gi.repository import Gtk as gtk
from gi.repository import AppIndicator3 as appindicator
from gi.repository import Notify as notify
from gi.repository import GObject

INDICATOR_ID = 'vtouchindicator'
SELF_DIR = os.path.dirname(os.path.abspath(__file__))
ICON_DEFAULT = os.path.join(SELF_DIR, 'assets/icons/icon_vtouch.svg')

evt_queue = mp.Queue()
last_timestamp = mp.Value('d', time.time())
framerate = mp.Value('i', 0)

def about(self):
    dialog = gtk.MessageDialog(
        transient_for=None,
        flags=0,
        message_type=gtk.MessageType.INFO,
        buttons=gtk.ButtonsType.OK,
        text="Jetson Virtual Touchpanel",
    )
    dialog.format_secondary_text(
        "This tool uses a camera to detect users' handpose to control the system mouse cursor. \
        \nIt is primarily designed for interactive signage systems, freeing users from physically touching a mouse or a touchpanel. \
        \n \
        \nhttps://github.com/NVIDIA-AI-IOT/jetson_virtual_touchpanel"
    )
    dialog.run()
    print("INFO dialog closed")

    dialog.destroy()

def start(_):
    cmd = "x-terminal-emulator --title='handpose-camera service' -e \
        /home/jetson/jetson-pose-container/run.sh \
        --run python3 ./_host_home/jetson_virtual_touchpanel/pub/trtpose_handpose/pub_hand_msg_thread.py \
        ".split()
    subprocess.call(cmd)

def stop(_):
    #cmd = "docker ps -a -q --filter ancestor=jetson-pose"
    cmd = "docker ps | grep 'jetson-pose' | awk '{print $1}'"
    container_id = subprocess.check_output(cmd, shell=True).decode("utf-8") 
    print(container_id)
    cmd = "docker stop " + container_id
    subprocess.call(cmd.split())

def quit(_):
    running.clear()
    proc_subscriber.terminate()
    evt_queue.put(None)
    gtk.main_quit()

def build_menu():
    menu = gtk.Menu()
    item_about = gtk.MenuItem('About Virtual Touchpanel ...')
    item_about.connect('activate', about)
    menu.append(item_about)
    
    menu.append(gtk.SeparatorMenuItem())

    item_start = gtk.MenuItem('Start camera-pose service')
    item_start.connect('activate', start)
    menu.append(item_start)
    item_stop = gtk.MenuItem('Stop camera-pose service')
    item_stop.connect('activate', stop)
    menu.append(item_stop)
    
    menu.append(gtk.SeparatorMenuItem())

    item_quit = gtk.MenuItem('Quit')
    item_quit.connect('activate', quit)
    menu.append(item_quit)

    menu.show_all()
    return menu

def mess_callback():
    pass

def trtpose_subscriber(running, last_timestamp, framerate):
    print("--- Subscriber thread ---")

    frame_number = 0 # number of message recived in the last 1 sec interval

    # Creates a socket instance
    context = zmq.Context()
    socket = context.socket(zmq.SUB)

    # Connects to a bound socket
    socket.connect("tcp://{}:{}".format(zmq_host, zmq_port))

    # Subscribes to all topics
    socket.subscribe("")

    last_gesture = ""
    curr_gesture = ""

    while True:

        # Receives a string format message
        msg = socket.recv_json() 
        cur_timestamp = time.time()
        curr_gesture = msg['gesture']
        
        x = msg['objects'][0]['keypoints'][5]['x']
        y = msg['objects'][0]['keypoints'][5]['y']
        #print("[" + str(x) + "," + str(y) + "] (received at " + str(cur_timestamp) + ")")
        if (x != 0 or y != 0):
            model.set_mouse_coord((224-x)/224 * 1920, y/224 * 1080)
            if ( last_gesture == "point" and curr_gesture == "click"):
                print(" ===========> trigger_mouse_click")
                model.trigger_mouse_click(1);
            last_gesture = curr_gesture

        if (cur_timestamp % 1.0 < last_timestamp.value % 1.0):
            framerate = frame_number
            print("framerate = " + str(framerate))
            frame_number = 0
        else:
            frame_number += 1

        last_timestamp.value = cur_timestamp

def trtpose_monitor(running, last_timestamp):
    print("--- Monitor process ---")
    trtpose_active = False
    while running.is_set():
        cur_timestamp = time.time()
        #print("cur: " + str(cur_timestamp) + ", last_timestamp: " + str(last_timestamp.value))
        if cur_timestamp - last_timestamp.value > 0.5:
            if trtpose_active == True:
                print("trt_pose stopped")
            trtpose_active = False
        else:
            if trtpose_active == False:
                print("trt_pose started")
            trtpose_active = True
        update_icon(trtpose_active)
        do_notify(trtpose_active)
        time.sleep(0.5)

def check_trtpose_activity():
    threading.Timer(1.0, check_trtpose_activity).start()
    print("Hello, World!" +  str(time.time()))

def update_icon(status):
    if(status):
        indicator.set_icon(os.path.join(SELF_DIR, 'assets/icons/icon_vtouch.svg'))
    else:
        indicator.set_icon(os.path.join(SELF_DIR, 'assets/icons/icon_vtouch_inactive.svg'))

def do_notify(status):
    msg_lines = []
    if(status):
        msg_lines.append(f"Service 'handpose-camera' started")
    else:
        msg_lines.append(f"Service 'handpose-camera' stopped")
    msg = '\n'.join(msg_lines)
    notification.update(msg)
    notification.set_timeout(1000) #milliseconds
    notification.set_urgency(0) 
    notification.show()

model = vt.vtouch()

indicator = appindicator.Indicator.new(INDICATOR_ID, ICON_DEFAULT, appindicator.IndicatorCategory.SYSTEM_SERVICES)
indicator.set_status(appindicator.IndicatorStatus.ACTIVE)
indicator.set_menu(build_menu())

notify.init(INDICATOR_ID)
notification = notify.Notification()

running = threading.Event()
running.set()

proc_subscriber = mp.Process(target=trtpose_subscriber, args=(running, last_timestamp, framerate))
proc_subscriber.start()
thrd_monitor = threading.Thread(target=trtpose_monitor, args=(running, last_timestamp))
thrd_monitor.start()

gtk.main()






