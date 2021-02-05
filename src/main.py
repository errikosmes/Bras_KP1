# Imports
import logging
import threading
from niryo_one_tcp_client import *
from niryo_one_camera import *
import cv2 as cv
import numpy as np
from time import sleep
from API.croisement import *
from API.draw_rectangle import *
from API.workspace_referential import *

# Inits
# Set robot address
robot_ip_address = "10.10.10.10"
#robot_ip_address = "169.254.200.200"

# Set Observation Pose. It's where the robot will be placed for streaming
observation_pose = PoseObject(
    x=0.2, y=0.0, z=0.34,
    roll=0, pitch=1.57, yaw=-0.2,
)


def select_and_pick(client):

    # Getting calibration param
    _, mtx, dist = client.get_calibration_object()
    # Moving to observation pose
    client.move_pose(*observation_pose.to_list())

    while "workspace_not_found" :
        
        # Getting image
        status, img_compressed = client.get_img_compressed()
        if status is not True:
            print("error with Niryo One's service")
            break

        img_raw = uncompress_image(img_compressed) # Uncompressing image
        img_undistort = undistort_image(img_raw, mtx, dist) # Undistorting
        workspace_found, res_img_markers = debug_markers(img_undistort) # Trying to find markers

        # Trying to extract workspace if possible
        if workspace_found: img_workspace = extract_img_workspace(img_undistort, workspace_ratio=1.0)
        else: img_workspace = None

        # - Display
        # Concatenating raw image and undistorted image
        concat_ims = concat_imgs((img_raw, img_undistort))

        # Concatenating extracted workspace with markers annotation
        if img_workspace is not None: res_img_markers = concat_imgs((res_img_markers, resize_img(img_workspace, height=res_img_markers.shape[0])))

        # Showing images
        show_img("Images raw & undistorted", concat_ims, wait_ms=0)

        if img_workspace is not None:
            line_img =resize_img(img_workspace, height=res_img_markers.shape[0])
            # line_img = cv.flip(line_img,1)
            # line_img = cv.flip(line_img,0)

            break
        else:
            line_img=None


    POI = line_inter(line_img) #Points Of Interest
    POISelected = []
    clickCoord = [0, 0]
    regionSize = 30 

    show_img('Workspace', line_img, wait_ms=10)
    cv2.setMouseCallback('Workspace', selectRectCallback, param=[POI, POISelected, regionSize]) 
    imgCached = line_img.copy()

    while True:
        # draw region of interest rectangles 
        for point in POI: 
            if point in POISelected: drawSelected(line_img, point, regionSize, POISelected.index(point))
            else: drawUnselected(line_img,point,regionSize)
        
        key = show_img('Workspace', line_img)
        line_img = imgCached.copy()

        if key in [27, ord('\n'), ord('\r'), ord("q")]:  # Will break loop if the user press Escape or Q
            break

    # # PICK FROM POISelected
    for point in POISelected :
        inter_1_x, inter_1_y= change_space(point[1],point[0],0.01,0) #revoir les offsets ?
        pick_pose = PoseObject(x=inter_1_x, y=inter_1_y, z=0.135,roll=-2.70, pitch=1.57, yaw=-2.7)
        client.pick_from_pose(*pick_pose.to_list())
        client.move_pose(*observation_pose.to_list())
        sleep(2)

    client.set_learning_mode(True)

if __name__ == '__main__' :
    # Connect to robot
    client = NiryoOneClient()
    client.connect(robot_ip_address)
    # Calibrate robot if robot needs calibration
    client.calibrate(CalibrateMode.AUTO)

    try :
        select_and_pick(client)
    except Exception as e:
        print(e)
        client.set_learning_mode(True)
   
    # Releasing connection
    client.quit()
    
    