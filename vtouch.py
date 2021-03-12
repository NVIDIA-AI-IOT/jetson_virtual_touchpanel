import os
import sys
import re
import subprocess
import fileinput
import pynput

from pynput.mouse import Button, Controller

class vtouch(object):

    def __init__(self):
        print("vtouch init")
        self.mouse = Controller()

    def set_mode(self, mode):
        print("vtouch.set_mode()")

    def set_screen_res(self, width, height):
        self.screen_width=width
        self.screen_height=height

    def trigger_mouse_click(self, num):
        self.mouse.click(Button.left, num)

    def set_mouse_coord(self, coord_x, coord_y):
        self.mouse.position = (coord_x, coord_y)

    def set_mouse_percent(self, percent_x, percent_y):
        print("vtouch.set_mouse_percent()")
        self.set_mouse_coord(width * percent_x, height * percent_y)

    def move_mouse_by(self, delta_x, delta_y):
        print("vtouch.move_mouse_by()")
