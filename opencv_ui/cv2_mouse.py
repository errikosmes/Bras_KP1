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
    # check if left mouse button was clicked and update PIO lists
    if event == cv2.EVENT_LBUTTONDOWN:
        POI = param[0]
        PIOSelected = param[1]
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
        param[1] = PIOSelected
        # print(clickCoord);

def drawSelected(img, rectCenter, size, nb):
    font      = cv2.FONT_HERSHEY_SIMPLEX
    offset    =  (20, -40)
    fontScale = 0.75
    fontColor = (0, 255, 0)
    lineType  = 2

    cv2.rectangle(img, (rectCenter[0]-size, rectCenter[1]-size), (rectCenter[0]+size, rectCenter[1]+size), (0, 255, 0), 3)
    # cv2.circle(img, (rectCenter[0]-size, rectCenter[1]-size), 15, (0, 255, 0), -1)
    cv2.putText(img, str(nb), (rectCenter[0]+offset[0], rectCenter[1]+offset[1]), font, fontScale,fontColor, lineType)

    return img

def drawUnselected(img, rectCenter, size):
    cv2.rectangle(img, (rectCenter[0]-size, rectCenter[1]-size), (rectCenter[0]+size, rectCenter[1]+size), (0, 0, 255), 3)
    return img

# init
POI = [(318, 387), (734, 387)] #Point Of Interest
POISelected = []
clickCoord = [0, 0]
regionSize = 30

# load example img
img = cv2.imread('grid_test.png', cv2.IMREAD_COLOR)
imgCached = img.copy()

# show image 
cv2.imshow('image', imgCached) # needs to be called before setMouseCallback
cv2.setMouseCallback('image', selectRectCallback, param=[POI, POISelected, regionSize]) 
   
# keep looping until the 'q' key is pressed
while True:
    # draw region of interest rectangles 
    for point in POI: 
        if point in POISelected: drawSelected(img, point, regionSize, POISelected.index(point))
        else: drawUnselected(img, point, regionSize)

	# display the image and wait for a keypress
    cv2.imshow("image", img)
    img = imgCached.copy()
    key = cv2.waitKey(10) & 0xFF
    
    if key in [27, ord("q")]:  # Will break loop if the user press Escape or Q
        break
    
  
# close all the opened windows. 
cv2.destroyAllWindows() 