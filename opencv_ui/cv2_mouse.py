import cv2
import numpy as np 

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
    # update PIO lists
    # to check if left mouse button was clicked 
    if event == cv2.EVENT_LBUTTONDOWN:
        POI = param[0]
        PIOSelected = param[1]
    
        clickCoord = [x, y]

        for point in POI:
            # check if point is inside current PIO region (PIO rectangle)
            if (inRectangle(point, 30, clickCoord)):
                # if it's selected remove from PIOSelected
                if point in POISelected: POISelected.remove(point)                
                # else add to PIOSelected
                else: POISelected.append(point)

        param[0] = POI
        param[1] = PIOSelected
        # print(clickCoord);

def drawSelected(img, rectCenter, size):
    cv2.rectangle(img, (rectCenter[0]-size, rectCenter[1]-size), (rectCenter[0]+size, rectCenter[1]+size), (0, 255, 0), 3)
    return img

def drawUnselected(img, rectCenter, size):
    cv2.rectangle(img, (rectCenter[0]-size, rectCenter[1]-size), (rectCenter[0]+size, rectCenter[1]+size), (0, 0, 255), 3)
    return img

# init
POI = [(318, 387), (734, 387)] #Point Of Interest
POISelected = []
clickCoord = [0, 0]

# load example img
img = cv2.imread('grid_test.png', cv2.IMREAD_COLOR)

# show image 
cv2.imshow('image', img) # needs to be called before setMouseCallback
cv2.setMouseCallback('image', selectRectCallback, param=[POI, POISelected]) 
   
# keep looping until the 'q' key is pressed
while True:
    # draw region of interest rectangles 
    for point in POI: 
        if point in POISelected: drawSelected(img, point, 30)
        else: drawUnselected(img, point, 30)

	# display the image and wait for a keypress
    cv2.imshow("image", img)
    key = cv2.waitKey(10) & 0xFF
  
# close all the opened windows. 
cv2.destroyAllWindows() 