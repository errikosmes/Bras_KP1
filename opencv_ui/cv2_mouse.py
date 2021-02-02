import cv2
import numpy as np 

#define the events for the 
# mouse_click. 
def select_rect(event, x, y, flags, param): 
    rectP1 = param[0]
    rectP2 = param[1]
    global clickInRect
    
    # to check if left mouse button was clicked 
    if event == cv2.EVENT_LBUTTONDOWN:
        clickCoord = [x, y]
        clickInRect = inRectangle(rectP1, rectP2, clickCoord)
        print(clickCoord);

def inRectangle(rectP1, rectP2, mouseCoord):
    if (mouseCoord[0]>min(rectP1[0], rectP2[0]) and mouseCoord[0]<max(rectP1[0], rectP2[0]) and mouseCoord[1]>min(rectP1[1], rectP2[1]) and mouseCoord[1]<max(rectP1[1], rectP2[1])):
        return True
    else: 
        return False


# init
rectP1 = (318-50, 386-50)
rectP2 = (318+50, 386+50)
param = (rectP1, rectP2)
selected = 0
clickInRect = False

img = cv2.imread('grid_test.png', cv2.IMREAD_COLOR)
cv2.rectangle(img, rectP1, rectP2, (0, 0, 255), 3)
# img = cv2.circle(img, rectP1, radius=3, color=(0, 0, 255), thickness=-1)
# img = cv2.circle(img, rectP2, radius=3, color=(0, 0, 255), thickness=-1)
clickCoord = [0, 0]
  
# show image 
cv2.imshow('image', img)
cv2.setMouseCallback('image', select_rect, param) 
   
# keep looping until the 'q' key is pressed
while True:
	# display the image and wait for a keypress
    cv2.imshow("image", img)
    if clickInRect: 
        if (selected):
            cv2.rectangle(img, rectP1, rectP2, (0, 0, 255), 3)
            selected = 0
        else: 
            cv2.rectangle(img, rectP1, rectP2, (0, 255, 0), 3)
            selected = 1
        clickInRect = False
    key = cv2.waitKey(1) & 0xFF
  
# close all the opened windows. 
cv2.destroyAllWindows() 