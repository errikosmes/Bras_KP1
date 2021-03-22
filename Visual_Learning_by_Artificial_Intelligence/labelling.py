import time
import math
import cv2
import os
from niryo_one_tcp_client import *
from niryo_one_camera import *
import utils

robot_ip_address = "10.10.10.10"  # Replace by robot ip address
workspace = "Workshop_v2"  # Name of your workspace

observation_pose_wkshop = PoseObject(
    x=-0.00, y=-0.17, z=0.28,
    roll=0.998, pitch=1.41, yaw=-0.76,
)


def labelling(client, name):
    try:
        os.mkdir("./data/" + name)
    except:
        pass
    print("label ", name)
    a, img_work = utils.take_workspace_img(client,1.5)

    mask = utils.objs_mask(img_work)

    debug = concat_imgs([img_work, mask], 1)
    if __name__ == '__main__':
        show_img("robot view", debug, wait_ms=1)
    objs = utils.extract_objs(img_work, mask)
    if len(objs) != 0:
        print(str(len(objs)) + " object detected")
        objs[0].img = resize_img(objs[0].img, width=64, height=64)
        if __name__ == '__main__':
            show_img("robot view2", img_work, wait_ms=50)
        print("saved", name)
        cv2.imwrite("./data/" + name + "/" + str(time.time()) + ".jpg", img_work)
    else:
        print(str(len(objs)) + " object detected")
    return img_work


if __name__ == '__main__':
    def Nothing(val):
        pass

    # Connecting to robot
    client = NiryoOneClient()
    client.connect(robot_ip_address)
    try:
        client.calibrate(CalibrateMode.AUTO)
        client.change_tool(RobotTool.VACUUM_PUMP_1)
    except:
        print("calibration failed")
    name = input("object name :")
    client.move_pose(*observation_pose_wkshop.to_list())
    try:
        os.mkdir("./data")
    except:
        pass
    try:
        os.mkdir("./data/" + name)
    except:
        pass
    a, img_work = utils.take_workspace_img(client,1.5)
    show_img("robot view", img_work, wait_ms=50)
    cv2.createTrackbar("threshold", "robot view", 130, 256, Nothing)
    while "user doesn't quit":
        n=input("press enter to take picture")
        if n=='q':
            break
        labelling(client, name)
    
    client.set_learning_mode(True)
    client.quit()