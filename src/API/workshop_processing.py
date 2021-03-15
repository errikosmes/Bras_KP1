# Imports
from niryo_one_tcp_client import *
from niryo_one_camera import *
import cv2 as cv
import numpy as np
import math
import os

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

import tensorflow as tf


objects_names = os.listdir("model IA/data/")
model = tf.keras.models.load_model('model IA/model')

def distance_euclidienne(p1,p2):

    X = (p1[0]-p2[0])**2
    Y = (p1[1]-p2[1])**2

    return math.sqrt(X+Y)

def keep_biggest_contours(img, bc):

    bc_recherche = bc.copy()
    new_bc = bc.copy()
    j=0
    while j < len(new_bc):
        for i in range(0,len(bc_recherche)):
            dist = distance_euclidienne(bc_recherche[j], bc_recherche[i])
            if(dist == 0):
                continue
            if dist < 75:
                new_bc.remove(bc_recherche[i])
        j+=1
    return new_bc

def find_objects_workshop_old(image,nb_objets=10):
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

    img= remove_shadows(image)

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

    for i in contours:
        angle = get_contour_angle(i)
        cx,cy = get_contour_barycenter(i)
        bc.append((cx,cy))
        angles.append(angle)

    cpt=0
    for (cx,cy) in bc:
        img = cv2.putText(img, str(cpt),(cx,cy),cv.FONT_HERSHEY_SCRIPT_SIMPLEX, 1,color=(0,0,0), thickness=2)
        cpt+=1


    return bc, angles

def find_objects_workshop(image):
    """
    Trouve les barycentres des objets du workshop
    Parameters
    ----------
    image : Frame

    Returns
    -------
    bc : Tableau des barycentres

    """
    img= remove_shadows(image)
    img = standardize_img(img)

    mask = objs_mask(img)
    objs = extract_objs(img, mask)
    cpt=0
    bc=[]
    angles=[]
    for obj in objs:
        img = cv2.putText(img, str(cpt),(obj.x,obj.y),cv.FONT_HERSHEY_SCRIPT_SIMPLEX, 1,color=(0,0,0), thickness=2)
        cpt+=1
        bc.append((obj.x,obj.y))
        angles.append(obj.angle)
    # plt.imshow(img)
    return bc, angles

def find_objects_workshop_ML(image):
    """
    Trouve les barycentres des objets du workshop
    Parameters
    ----------
    image : Frame

    Returns
    -------
    bc : Tableau des barycentres

    """
    def get_objs(img):
        img = standardize_img(img)
        mask = objs_mask(img)
        objs = extract_objs(img, mask)
        return objs

    img=image
    img_rs= remove_shadows(image)

    objs_ml = get_objs(img)
    objs_rs = get_objs(img_rs)

    cpt=0
    bc=[]
    angles=[]

    imgs = []
    #resize all objects img to 64*64 pixels
    for x in range(len(objs_ml)):
        imgs.append(resize_img(objs_ml[x].img, width=64, height=64))

    imgs = np.array(imgs)

    #predict all the images
    try:
        predictions = model.predict(imgs)
    except:
        predictions=[]
    objs_pred = []
    for x in range(len(predictions)):
        obj = objs_ml[x]
        pred = predictions[x].argmax()
        objs_pred.append([objects_names[pred],(obj.x,obj.y)])


    for x in range(len(objs_rs)):
        obj = objs_rs[x]
        bc.append((obj.x,obj.y))
        angles.append(obj.angle)

    # plt.imshow(img)
    return bc, angles, objs_pred



def get_obj_pose(client, workspace, image,nb_objet=3):
    # seuil_px, comparaison obj prédit et autres
    # bc, angles = find_objects_workshop(image)
    seuil_px = 30
    preds = []
    bc, angles, preds = find_objects_workshop_ML(image)

    new_preds = preds.copy()

    objs_pose=[]
    for i in range(len(bc)):

        x,y = relative_pos_from_pixels(image,bc[i][0],bc[i][1])

        status, obj_pose = client.get_target_pose_from_rel(workspace, 0.0, x, y, angles[i])

        objs_pose.append(([obj_pose], bc[i]))

    for obj_p in range(0,len(preds)):
        pt_pred = preds[obj_p][1]
        for pt_obj in bc:
            d = distance_euclidienne(pt_pred,pt_obj)
            if d < 30:
                new_preds[obj_p][1] = pt_obj
                break

    return objs_pose, bc, new_preds


# rotate a numpy img
def rotate_image(image, angle):
    image_center = tuple(np.array(image.shape[1::-1]) / 2)
    rot_mat = cv2.getRotationMatrix2D(image_center, angle, 1.0)
    result = cv2.warpAffine(image, rot_mat, image.shape[1::-1], flags=cv2.INTER_LINEAR)
    return result


class CameraObject(object):
    def __init__(self, img, x=None, y=None, angle=None, cnt=None, box=None, square=None):
        self.img = img
        self.angle = angle
        self.x = x
        self.y = y
        self.cnt = cnt
        self.box = box
        self.square = square
        self.type = None

def threshold_hls(img, list_min_hsv, list_max_hsv):
    frame_hsl = cv2.cvtColor(img, cv2.COLOR_BGR2HLS)
    return cv2.inRange(frame_hsl, tuple(list_min_hsv), tuple(list_max_hsv))

def fill_holes(img):
    im_floodfill = img.copy()
    h, w = img.shape[:2]
    mask = np.zeros((h + 2, w + 2), np.uint8)
    cv2.floodFill(im_floodfill, mask, (0, 0), 255)
    im_floodfill_inv = cv2.bitwise_not(im_floodfill)
    img = img | im_floodfill_inv
    return (img)

def extract_objs(img, mask):
    cnts, hierarchy = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

    objs = []

    initial_shape = img.shape

    #surround the image with Black pixels
    blank = np.zeros(img.shape, np.uint8)
    img = concat_imgs([blank, img, blank], 0)
    blank = np.zeros(img.shape, np.uint8)
    img = concat_imgs([blank, img, blank], 1)

    #for all the contour in the image, copy the corresponding object
    if cnts is not None:
        for cnt in cnts:
            cx, cy = get_contour_barycenter(cnt)

            try:
                angle = get_contour_angle(cnt)
                angle+=0.1
            except:
                angle = 0

            #get the minimal Area Rectangle around the contour
            rect = cv2.minAreaRect(cnt)
            box = cv2.boxPoints(rect)
            box = np.int0(box)

            up = int(box[0][1])
            down = int(box[2][1])
            left = int(box[1][0])
            right = int(box[3][0])

            size_x = right - left
            size_y = up - down

            #verify that our objects is not just a point or a line
            if size_x <= 0 or size_y <= 0:
                continue

            #transform our rectangle into a square
            if size_x > size_y:
                down -= int((size_x - size_y) / 2)
                size = size_x
            else:
                left -= int((size_y - size_x) / 2)
                size = size_y

            #if the square is to small, skip it
            if size < 64:
                continue

            square = [[down, left], [left + size, down + size]]

            #copy the pixels of our rectangle in a new image
            down += initial_shape[0]
            left += initial_shape[1]
            img_cut = np.zeros((size, size, 3), np.uint8)
            img_cut[:, :] = img[down: down + size, left: left + size]

            #rotate the image so the object is in a vertical orientation
            # img_cut = rotate_image(img_cut, angle * 180 / math.pi)

            #append the data and the image of our object
            objs.append(CameraObject(img_cut, cx, cy, angle, cnt, box, square))
    return objs

def objs_mask(img):
    color_hls = [[0, 0, 0], [360, 210, 255]]

    mask = threshold_hls(img, *color_hls)

    kernel3 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    kernel5 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    kernel7 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    kernel11 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (11, 11))

    # erode workspace markers
    mask[:15, :] = cv2.erode(mask[:15, :], kernel7, iterations=5)
    mask[-15:, :] = cv2.erode(mask[-15:, :], kernel7, iterations=5)
    mask[:, :15] = cv2.erode(mask[:, :15], kernel7, iterations=5)
    mask[:, -15:] = cv2.erode(mask[:, -15:], kernel7, iterations=5)

    mask = fill_holes(mask)

    mask = cv2.dilate(mask, kernel3, iterations=1)
    mask = cv2.erode(mask, kernel5, iterations=1)
    mask = cv2.dilate(mask, kernel11, iterations=1)

    mask = fill_holes(mask)

    mask = cv2.erode(mask, kernel7, iterations=1)

    return mask

def standardize_img(img):
    array_type = img.dtype

    # color balance normalizing
    color_mean = np.mean(img, axis=(0, 1))
    mean_color_mean = np.mean(color_mean)
    img = img[:][:]*mean_color_mean/color_mean

    # color range normalizing
    min, max = np.quantile(img, [0.001, 0.95])
    img = (img - min) * 256 / (max - min)
    img = np.clip(img, 0, 255)
    img = img.astype(array_type)
    return img

def remove_shadows(img):
    rgb_planes = cv.split(img)
    result_planes = []

    for plane in rgb_planes:
        dilated_img = cv.dilate(plane, np.ones((7,7), np.uint8))
        bg_img = cv.medianBlur(dilated_img, 11)
        diff_img = 255 - cv.absdiff(plane, bg_img)
        result_planes.append(diff_img)

    result = cv.merge(result_planes)
    return(result)

# wkshop = "Workshop_v2"
# robot_ip_address = "10.10.10.10"

# if __name__ == '__main__' :
#     # Connect to robot
#     client = NiryoOneClient()
#     client.connect(robot_ip_address)
#     # Calibrate robot if robot needs calibration
#     client.calibrate(CalibrateMode.AUTO)
#     a,bc = get_obj_pose(client, wkshop, image, 3)
#     client.quit()
