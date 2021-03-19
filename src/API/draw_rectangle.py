"""
draw_rectangle.py : This is file is used to write on image and interact with user
@authors: BORDEAU Raphaël - DE LA FUENTE Léo - GOURJON Amélie - MESSARA Errikos - PAGNY Louis
"""

import cv2 as cv
import numpy as np


def writeNames(img, preds,size):
    """
    Write names of the objects predicted on image

    """
    offset_y=20
    for elt in preds:
        img = cv.putText(img,elt[0].replace('_',' '), (elt[1][0]-size,elt[1][1]+size+offset_y) , cv.FONT_HERSHEY_SIMPLEX, 0.6,(0,255,255),2)
        
def drawUnselected(img, rectCenter, size):
    """
    Draw a red rectangle on image

    """
    img=cv.rectangle(img, (int(rectCenter[0])-size, int(rectCenter[1])-size), (int(rectCenter[0])+size, int(rectCenter[1])+size), (0, 0, 255), 3)
    return img

def inRectangle(ctrCoord, size, mouseCoord):
    """
    check if (mouseCoord) are inside a rectangle of centre (ctrCoord) and size (size)

    """
    # 
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
    """
    check if left mouse button was clicked and update PIO lists

    """
    if event == cv.EVENT_LBUTTONDOWN:
        POI = param[0]
        POISelected = param[1]
        regionSize = param[2]
    
        clickCoord = [x, y]

        for point in POI:
            point=tuple(point)
            # check if point is inside current PIO region (PIO rectangle)
            if (inRectangle(point, regionSize, clickCoord)):
                # if it's selected remove from PIOSelected
                if point in POISelected: POISelected.remove(point)                
                # else add to PIOSelected
                else: POISelected.append(point)

        param[0] = POI
        param[1] = POISelected

def drawSelected(img, rectCenter, size, nb):
    """
    Draw a green rectangle on image

    """
    font      = cv.FONT_HERSHEY_SIMPLEX
    offset    = (20, -40)
    fontScale = 0.75
    fontColor = (0, 255, 0)
    lineType  = 2

    cv.rectangle(img, (int(rectCenter[0])-size, int(rectCenter[1])-size), (int(rectCenter[0])+size, int(rectCenter[1])+size), (0, 255, 0), 3)
    cv.putText(img, str(nb), (int(rectCenter[0])+offset[0], int(rectCenter[1])+offset[1]), font, fontScale,fontColor, lineType)

    return img