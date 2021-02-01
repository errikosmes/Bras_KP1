#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Jan 29 14:06:44 2021

@author: leo
"""
# Imports
from niryo_one_tcp_client import *
from niryo_one_camera import *

import cv2
import sys
from PyQt5.QtWidgets import  QWidget, QLabel, QApplication
from PyQt5.QtCore import QThread, Qt, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QImage, QPixmap

# Set robot address
robot_ip_address = "169.254.200.201"

# Set Observation Pose. It's where the robot will be placed for streaming
observation_pose = PoseObject(
    x=0.2, y=0.0, z=0.34,
    roll=0, pitch=1.57, yaw=-0.2,
)


def video_stream(niryo_one_client):
    # Getting calibration param
    _, mtx, dist = niryo_one_client.get_calibration_object()
    # Moving to observation pose
    niryo_one_client.move_pose(*observation_pose.to_list())

    while "User do not press Escape neither Q":
        # Getting image
        status, img_compressed = niryo_one_client.get_img_compressed()
        if status is not True:
            print("error with Niryo One's service")
            break
        # Uncompressing image
        img_raw = uncompress_image(img_compressed)
        # Undistorting
        img_undistort = undistort_image(img_raw, mtx, dist)
        # Trying to find markers
        workspace_found, res_img_markers = debug_markers(img_undistort)
        # Trying to extract workspace if possible
        if workspace_found:
            img_workspace = extract_img_workspace(img_undistort, workspace_ratio=1.0)
        else:
            img_workspace = None

        # - Display
        # Concatenating raw image and undistorted image
        concat_ims = concat_imgs((img_raw, img_undistort))
        # Concatenating extracted workspace with markers annotation
        if img_workspace is not None:
            res_img_markers = concat_imgs((res_img_markers, resize_img(img_workspace, height=res_img_markers.shape[0])))

        # Showing images
        show_img("Images raw & undistorted", concat_ims, wait_ms=0)
        key = show_img("Markers", res_img_markers, wait_ms=30)

        if key in [27, ord("q")]:  # Will break loop if the user press Escape or Q
            break

    niryo_one_client.set_learning_mode(True)



class Thread(QThread):
    changePixmap = pyqtSignal(QImage)
    client = NiryoOneClient()
    client.connect(robot_ip_address)
    # Calibrate robot if robot needs calibration
    
    
    def run(self):
        niryo_one_client = client
        _, mtx, dist = niryo_one_client.get_calibration_object()
        niryo_one_client.move_pose(*observation_pose.to_list())
        while "User do not press Escape neither Q":
            # Getting image
            status, img_compressed = niryo_one_client.get_img_compressed()
            if status is not True:
                print("error with Niryo One's service")
                break
            # Uncompressing image
            img_raw = uncompress_image(img_compressed)
            # Undistorting
            img_undistort = undistort_image(img_raw, mtx, dist)
            
            rgbImage = cv2.cvtColor(img_undistort, cv2.COLOR_BGR2RGB)
            h, w, ch = rgbImage.shape
            bytesPerLine = ch * w
            convertToQtFormat = QImage(rgbImage.data, w, h, bytesPerLine, QImage.Format_RGB888)
            p = convertToQtFormat.scaled(640, 480, Qt.KeepAspectRatio)
            self.changePixmap.emit(p)
            
            if key in [27, ord("q")]:  # Will break loop if the user press Escape or Q
                break
                


class App(QWidget):
    def __init__(self):
        super().__init__()
        self.title = 'PyQt5 Video'
        self.left = 100
        self.top = 100
        self.width = 640
        self.height = 480
        self.initUI()


    @pyqtSlot(QImage)
    def setImage(self, image):
        self.label.setPixmap(QPixmap.fromImage(image))

    def initUI(self):
        self.setWindowTitle(self.title)
        self.setGeometry(self.left, self.top, self.width, self.height)
        self.resize(1800, 1200)
        # create a label
        self.label = QLabel(self)
        self.label.move(280, 120)
        self.label.resize(640, 480)
        th = Thread(self)
        th.changePixmap.connect(self.setImage)
        th.start()
        self.show()
        
if __name__ == '__main__':
    
    app = QApplication(sys.argv)
    ex = App()
    sys.exit(app.exec_())