"""
This script allows to capture Niryo One's video streaming and to make some image processing on it
"""

# Imports
from niryo_one_tcp_client import *
from niryo_one_camera import *
import cv2 as cv
import numpy as np
from time import sleep

# Set robot address
#robot_ip_address = "10.10.10.10"
robot_ip_address = "169.254.200.200"
#testde ces grand mort

# Set Observation Pose. It's where the robot will be placed for streaming
observation_pose = PoseObject(
    x=0.2, y=0.0, z=0.34,
    roll=0, pitch=1.57, yaw=-0.2,
)



def change_space(px_x,px_y,offset_x=0,offset_y=0):
    lg_x = 0.178
    lg_y = 0.188
    size_img = 480

    xi = px_x*(lg_x/size_img)
    yi = px_y*(lg_y/size_img)

    x0 = 0.163
    y0=-0.093

    x=xi+x0+offset_x
    y=yi+y0+offset_x

    return x,y

def clean_line(img,lines):
    lines_cpy= np.copy(lines)

    for i in range ( len(lines) ):
        for j in range ( len(lines) ):
            if (i!=j) and (lines[i][0][0] / lines[j][0][0] <= 1.13) and  (lines[i][0][0] / lines[j][0][0] >= 0.9) :
                if ( (lines_cpy[j][0][0]!= 0) and ( lines_cpy[i][0][0]!=0) ):
                    lines_cpy[j][0][0]= 0


    lines_net=[i for i in lines_cpy if int(i[0][0]) != 0 and (int(i[0][0]) <=len(img[0])-5) ]
    print('Clean lines ok')
    return lines_net


def find_croisement(lines):
    horiz =[]
    vert = []
    inter=[]
    for i in lines:
        if i[0][1] < 0.5 and i[0][1] > -0.5:
            horiz.append(i)
        elif i[0][1] < np.pi/2 + 0.1 and i[0][1] > np.pi/2 - 0.1 :
            vert.append(i)
        else:
            print('Droite ni horizontale ni verticale',i)

    for i in range ( len(horiz)  ):
        x0i= np.cos(horiz[i][0][1]) * horiz[i][0][0]
        y0i= np.sin(horiz[i][0][1]) * horiz[i][0][0]
        for j in range ( len(vert) ):
            y0j= np.sin(vert[j][0][1]) * vert[j][0][0]
            inter.append((x0i, y0i+y0j))
    print('Find croisement ok')
    return(inter)

def line_inter(line_img):

    gray = cv.cvtColor(line_img,cv.COLOR_BGR2GRAY)
    edges = cv.Canny(gray,50,150,apertureSize = 3)
    lines = cv.HoughLines(edges,1,np.pi/180,300)
    if lines is None:
        return None
    lines_net = clean_line(line_img,lines)
    inter = find_croisement(lines_net)
    for i in range ( len(lines_net) ):
        for rho,theta in lines_net[i]:
            print('Lines :', i)
            a = np.cos(theta)
            b = np.sin(theta)
            x0 = a*rho
            y0 = b*rho
            x1 = int(x0 + 1000*(-b))
            y1 = int(y0 + 1000*(a))
            x2 = int(x0 - 1000*(-b))
            y2 = int(y0 - 1000*(a))
                # and (y0 <= 10):
            cv2.line(line_img,(x1,y1),(x2,y2),(0,0,255),1)

    return inter

def circle_inter(line_img,inter):
    cpt=0
    for i in inter:
        print(cpt,' : Inter:',i)
        line_img = cv2.circle(line_img, i , radius=15, color=(0, 255, 255), thickness=2)
        line_img = cv2.putText(line_img, str(cpt) , i, cv2.FONT_HERSHEY_SIMPLEX , 2, color=(0,0,0), thickness=3)
        cpt+=1


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

        if img_workspace is not None:
            line_img =resize_img(img_workspace, height=res_img_markers.shape[0])
            # line_img = cv.flip(line_img,1)
        else:
            line_img=None


        if line_img is not None:
            inter = line_inter(line_img)
            circle_inter(line_img,inter)
            show_img('Workspace', line_img, wait_ms=10)

        # PICK FROM X,Y
            while True:
                print("Nb de croisement :",len(inter))
                usr_inter = input()
                if(usr_inter=='q'):
                    break

                usr_inter = inter[int(usr_inter)]

                inter_1_x, inter_1_y= change_space(usr_inter[1],usr_inter[0],0.01,0)
                pick_pose = PoseObject(
                    x=inter_1_x, y=inter_1_y, z=0.135,
                    roll=-2.70, pitch=1.57, yaw=-2.7
                )
                niryo_one_client.pick_from_pose(*pick_pose.to_list())

                niryo_one_client.move_pose(*observation_pose.to_list())


        sleep(5)
        key = show_img("Markers", res_img_markers, wait_ms=10)
        if key in [27, ord("q")]:  # Will break loop if the user press Escape or Q
            break

    niryo_one_client.set_learning_mode(True)


if __name__ == '__main__':
    # Connect to robot
    client = NiryoOneClient()
    client.connect(robot_ip_address)
    # Calibrate robot if robot needs calibration
    # client.calibrate(CalibrateMode.AUTO)
    # Launching main process
    video_stream(client)
    # Releasing connection
    client.quit()
