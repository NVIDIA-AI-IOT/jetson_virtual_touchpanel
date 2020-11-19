import os
import sys
import re
import subprocess
import fileinput
import pynput

class vtouch(object):

    def __init__(self):
        print("vtouch init")

    def set_mode(self, mode):
        print("vtouch.set_mode()")

    def set_mouse_coord(self, coord_x, coord_y):
        print("vtouch.set_mouse_coord()")

    def move_mouse_by(self, delta_x, delta_y):
        print("vtouch.move_mouse_by()")
