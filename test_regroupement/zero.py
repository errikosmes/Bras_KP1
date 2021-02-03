# Imports
from niryo_one_tcp_client import *
from niryo_one_camera import *
import cv2 as cv
import numpy as np
from time import sleep
import time

# Set robot address
#robot_ip_address = "10.10.10.10"
robot_ip_address = "169.254.200.200"

client = NiryoOneClient()
client.connect(robot_ip_address)
client.set_learning_mode(True)
