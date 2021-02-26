# Imports
from niryo_one_tcp_client import *
from niryo_one_camera import *
import cv2 as cv
import numpy as np

def find_objects_workshop(image,nb_objets):
    """
    Trouve les barycentres des objets du workshop
    Parameters
    ----------
    image : Frame
    nb_objets : Nombre d'objets du workshop

    Returns
    -------
    bc : Tableau des barycentres

    """
    
    img= image
    
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    mask = gray > 170    
    img_mask = gray * mask
    
    objs = (img_mask == 0)*255
    objs = objs.astype(np.uint8)    
    contours = biggest_contours_finder(objs,nb_contours_max=nb_objets)    
    # cv.drawContours(image, contours, -1, (0,255,0),3)
    
    # Barycenters
    bc = []
    angles = []
    cpt=0
    for i in contours:
        angle = get_contour_angle(i)
        cx,cy = get_contour_barycenter(i)
        img = cv2.putText(img, str(cpt),(cx,cy),cv.FONT_HERSHEY_SCRIPT_SIMPLEX, 1,color=(0,0,0), thickness=2)
        bc.append((cx,cy))
        angles.append(angle)
        cpt+=1
    
    return bc, angles


def get_obj_pose(client, workspace, image, nb_objet):
    
    bc, angles = find_objects_workshop(image,nb_objet)
    
    objs_pose=[]
    for i in range(len(bc)):
        
        x,y = relative_pos_from_pixels(image,bc[i][0],bc[i][1])
        
        status, obj_pose = client.get_target_pose_from_rel(workspace, 0.0, x, y, angles[i])
         
        objs_pose.append(([obj_pose], bc[i]))
        
    return objs_pose, bc
        

# wkshop = "Workshop_v2"
# image = cv2.imread('images/IMG_ref.PNG')
# robot_ip_address = "10.10.10.10"

# if __name__ == '__main__' :
#     # Connect to robot
#     client = NiryoOneClient()
#     client.connect(robot_ip_address)
#     # Calibrate robot if robot needs calibration
#     client.calibrate(CalibrateMode.AUTO)
#     a,bc = get_obj_pose(client, wkshop, image, 3)
#     client.quit()


