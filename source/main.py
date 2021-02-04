# Imports
from niryo_one_tcp_client import *
from niryo_one_camera import *
import cv2 as cv
import numpy as np
from time import sleep


# Inits
# Set robot address
#robot_ip_address = "10.10.10.10"
robot_ip_address = "169.254.200.200"

# Set Observation Pose. It's where the robot will be placed for streaming
observation_pose = PoseObject(
    x=0.2, y=0.0, z=0.34,
    roll=0, pitch=1.57, yaw=-0.2,
)

# Functions
def change_space(px_x, px_y, offset_x=0, offset_y=0):
    lg_x = 0.178
    lg_y = 0.188
    size_img = 480

    xi = px_x*(lg_x/size_img)
    yi = px_y*(lg_y/size_img)

    x0 = 0.163
    y0 = -0.093

    x = xi+x0+offset_x
    y = yi+y0+offset_x

    return x, y

def clean_line(img,lines):
    lines_cpy= np.copy(lines)

    for i in range (len(lines)):
        for j in range (len(lines)):
            if (i!=j) and (lines[i][0][0] / lines[j][0][0] <= 1.13) and  (lines[i][0][0] / lines[j][0][0] >= 0.9) :
                if ((lines_cpy[j][0][0]!= 0) and (lines_cpy[i][0][0]!=0)):
                    lines_cpy[j][0][0]= 0


    lines_net = [i for i in lines_cpy if int(i[0][0]) != 0 and (int(i[0][0]) <=len(img[0])-5)]
    print('Clean lines ok')
    
    return lines_net

def find_croisement(lines):
    horiz = []
    vert = []
    inter = []

    for i in lines:
        if i[0][1] < 0.5 and i[0][1] > -0.5:
            horiz.append(i)
        elif i[0][1] < np.pi/2 + 0.1 and i[0][1] > np.pi/2 - 0.1 :
            vert.append(i)
        else:
            print('Droite ni horizontale ni verticale',i)

    for i in range (len(horiz)):
        x0i = np.cos(horiz[i][0][1]) * horiz[i][0][0]
        y0i = np.sin(horiz[i][0][1]) * horiz[i][0][0]

        for j in range (len(vert)):
            y0j = np.sin(vert[j][0][1]) * vert[j][0][0]
            inter.append((int(x0i), int(y0i+y0j)))
    
    print('Find croisement ok')
    return(inter)

def line_inter(line_img):
    gray = cv.cvtColor(line_img, cv.COLOR_BGR2GRAY)
    edges = cv.Canny(gray, 50, 150, apertureSize = 3)
    lines = cv.HoughLines(edges, 1, np.pi/180, 300)
    
    if lines is None: return None

    lines_net = clean_line(line_img, lines)
    inter = find_croisement(lines_net)

    for i in range (len(lines_net)):
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
            cv2.line(line_img, (x1,y1), (x2,y2), (0,0,255), 1)

    return inter

def drawUnselected(img, rectCenter, size):
    cv2.rectangle(img, (rectCenter[0]-size, rectCenter[1]-size), (rectCenter[0]+size, rectCenter[1]+size), (0, 0, 255), 3)
    return img

def inRectangle(ctrCoord, size, mouseCoord):
    # check if (mouseCoord) are inside a rectangle of centre (ctrCoord) and size (size)
    x1 = ctrCoord[0]-size
    y1 = ctrCoord[1]-size
    x2 = ctrCoord[0]+size
    y2 = ctrCoord[1]+size

    if (mouseCoord[0]>min(x1, x2) and mouseCoord[0]<max(x1, x2) and mouseCoord[1]>min(y1, y2) and mouseCoord[1]<max(y1, y2)):
        return True
    else: 
        return False

# define the events for the mouse_click. 
def selectRectCallback(event, x, y, flags, param):
    # check if left mouse button was clicked and update PIO lists
    if event == cv2.EVENT_LBUTTONDOWN:
        POI = param[0]
        POISelected = param[1]
        regionSize = param[2]
    
        clickCoord = [x, y]

        for point in POI:
            # check if point is inside current PIO region (PIO rectangle)
            if (inRectangle(point, regionSize, clickCoord)):
                # if it's selected remove from PIOSelected
                if point in POISelected: POISelected.remove(point)                
                # else add to PIOSelected
                else: POISelected.append(point)

        param[0] = POI
        param[1] = POISelected
        # print(clickCoord);

def drawSelected(img, rectCenter, size, nb):
    font      = cv2.FONT_HERSHEY_SIMPLEX
    offset    = (20, -40)
    fontScale = 0.75
    fontColor = (0, 255, 0)
    lineType  = 2

    cv2.rectangle(img, (rectCenter[0]-size, rectCenter[1]-size), (rectCenter[0]+size, rectCenter[1]+size), (0, 255, 0), 3)
    # cv2.circle(img, (rectCenter[0]-size, rectCenter[1]-size), 15, (0, 255, 0), -1)
    cv2.putText(img, str(nb), (rectCenter[0]+offset[0], rectCenter[1]+offset[1]), font, fontScale,fontColor, lineType)

    return img


def select_and_pick(client) :

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
        sleep(5)

    client.set_learning_mode(True)

if __name__ == '__main__' :
    # Connect to robot
    client = NiryoOneClient()
    client.connect(robot_ip_address)
    # Calibrate robot if robot needs calibration
    client.calibrate(CalibrateMode.AUTO)

    try :
        select_and_pick(client)
    except :
        client.set_learning_mode(True)
   
    # Releasing connection
    client.quit()

